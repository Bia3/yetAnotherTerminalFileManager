# My own file browser with image preview support and application bindings
import os.path
import sys

from magic import from_file as magic_from_file, from_buffer as magic_from_buffer

from PIL import Image

from rich.syntax import Syntax
from rich.text import Text
from rich.traceback import Traceback
from rich.markdown import Markdown

from textual.app import App, ComposeResult
from textual.reactive import var, Reactive
from textual.widgets import Header, Footer, Static, DirectoryTree
from textual.containers import VerticalScroll, Container


class FileBrowser(App):
    """A Textual app to manage a File Browser."""

    CSS_PATH = "file_browser.tcss"
    BINDINGS = [
        ("q", "quit", "Quit")

    ]

    show_tree = var(True)

    def watch_show_tree(self, show_tree: bool) -> None:
        """Called when show_tree is modified."""
        self.set_class(show_tree, "-show-tree")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        path = os.path.abspath("./") if len(sys.argv) < 2 else sys.argv[1]
        yield Header()
        with Container():
            yield DirectoryTree(path, id="tree-view")
            with VerticalScroll(id="code-view"):
                yield Static(id="code", expand=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(DirectoryTree).focus()

    @staticmethod
    def img_to_string(img: Image, dest_width: int, unicode: bool = True) -> str:
        img_width, img_height = img.size
        scale = img_width / dest_width
        dest_height = int(img_height / scale)
        dest_height = dest_height + 1 if dest_height % 2 != 0 else dest_height
        img = img.resize((dest_width, dest_height))
        output = ""

        for y in range(0, dest_height, 2):
            for x in range(dest_width):
                if unicode:
                    r1, g1, b1 = img.getpixel((x, y))
                    r2, g2, b2 = img.getpixel((x, y + 1))
                    output = output + f"[rgb({r1},{g1},{b1}) on rgb({r2},{g2},{b2})]▀[/]"
                else:
                    r, g, b = img.getpixel((x, y))
                    output = output + f"[on rgb({r},{g},{b})] [/]"

            output = output + "\n"

        return output

    def on_exception(self, view) -> None:
        view.update(Traceback(theme="github-dark", width=None))
        text = Text.assemble(("ERROR ", "bold red"), Text.from_markup(":warning-emoji:"))
        self.sub_title = text

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Called when the user click a file in the directory tree."""
        event.stop()
        preview = self.query_one("#code", Static)

        mime = magic_from_file(event.path, mime=True)
        tlt = mime.split('/')[0]

        match tlt:
            case 'application':
                self.on_code_view(event)
            case 'text':
                self.on_text(mime, event)
            case 'image':
                self.on_image_view(event)
            case _:
                preview.update(mime)
                self.sub_title = Reactive("Mime Type")

    def on_text(self, mime: str, event: DirectoryTree.FileSelected) -> None:
        match mime:
            case 'text/plain':
                self.on_text_plain(mime, event)
            case _:
                self.on_code_view(event)

    def on_text_plain(self, mime: str, event: DirectoryTree.FileSelected) -> None:
        preview = self.query_one("#code", Static)
        match mime:
            case 'text/plain':
                file_ext = os.path.basename(event.path).split('.')
                if len(file_ext) > 1:
                    self.on_t_plain_ext(file_ext[1], event)
                else:
                    magic_from_buffer(open(event.path, "rb").read(2048), mime=True)
                    preview.update(mime)
                    self.sub_title = Reactive("Mime Type")
                    # self.on_code_view(event)
            case _:
                self.on_code_view(event)

    def on_t_plain_ext(self, file_ext: str, event: DirectoryTree.FileSelected) -> None:
        match file_ext:
            case 'md':
                self.on_markdown_view(event)
            case _:
                self.on_code_view(event)

    def on_markdown_view(self, event: DirectoryTree.FileSelected) -> None:
        preview = self.query_one("#code", Static)
        viewbox = preview.parent
        try:
            with open(event.path, 'r') as f:
                markup = f.read().replace('-[ ]', '- ☐').replace('-[x]', '- ☒')
                markdown = Markdown(
                    markup=markup,
                    code_theme="github-dark",
                    inline_code_theme="github-dark"
                )
        except Exception:
            self.on_exception(preview)
        else:
            viewbox.add_class('code-view')
            viewbox.remove_class('image-view')
            preview.remove_class('image')
            preview.update(markdown)
            self.query_one("#code-view").scroll_home(animate=False)
            self.sub_title = str(event.path)

    def on_code_view(self, event: DirectoryTree.FileSelected) -> None:
        preview = self.query_one("#code", Static)
        viewbox = preview.parent
        try:
            syntax = Syntax.from_path(
                str(event.path),
                line_numbers=True,
                word_wrap=False,
                indent_guides=True,
                theme="github-dark",
            )
        except Exception:
            self.on_exception(preview)
        else:
            viewbox.add_class('code-view')
            viewbox.remove_class('image-view')
            preview.remove_class('image')
            preview.update(syntax)
            self.query_one("#code-view").scroll_home(animate=False)
            self.sub_title = str(event.path)

    def on_image_view(self, event: DirectoryTree.FileSelected) -> None:
        preview = self.query_one("#code", Static)
        viewbox = preview.parent
        try:
            image = Image.open(event.path)
            image_view = self.img_to_string(img=image,
                                            dest_width=80)
        except Exception:
            self.on_exception(preview)
        else:
            viewbox.remove_class('code-view')
            viewbox.add_class('image-view')
            preview.add_class('image')
            preview.update(image_view)
            self.sub_title = str(event.path)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    app = FileBrowser()
    app.run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
