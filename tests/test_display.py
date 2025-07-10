"""Tests for the display system."""

import pytest
import base64
from unittest.mock import Mock, patch

from src.plaque.display import to_renderable
from src.plaque.renderables import (
    HTML,
    Markdown,
    Text,
    PNG,
    JPEG,
    SVG,
    Latex,
    JSON,
)


# Mock optional dependencies for tests
@pytest.fixture(autouse=True)
def mock_optional_imports(monkeypatch):
    # Create mock classes for isinstance checks
    mock_figure_class = type("Figure", (), {"savefig": Mock()})
    mock_dataframe_class = type(
        "DataFrame", (), {"to_html": Mock(return_value="<table>...</table>")}
    )
    mock_image_class = type("Image", (), {"save": Mock()})

    # Mock the modules and their internal classes
    mock_matplotlib = Mock()
    mock_matplotlib.figure.Figure = mock_figure_class

    mock_pd = Mock()
    mock_pd.DataFrame = mock_dataframe_class

    mock_pil = Mock()
    mock_pil.Image = mock_image_class

    monkeypatch.setattr("src.plaque.display.matplotlib", mock_matplotlib)
    monkeypatch.setattr("src.plaque.display.pd", mock_pd)
    monkeypatch.setattr("src.plaque.display.Image", mock_pil)
    # Also patch the plt.close call to avoid errors with mock objects
    monkeypatch.setattr("src.plaque.display.plt", Mock())


class TestToRenderable:
    """Test the main to_renderable function."""

    def test_display_method_priority(self):
        """Test that _display_() method takes priority and is recursively rendered."""

        class InnerObject:
            def _repr_html_(self):
                return "<p>Inner HTML</p>"

        class TestObject:
            def _display_(self):
                return InnerObject()

            def _repr_html_(self):
                return "<p>Outer HTML</p>"

        obj = TestObject()
        renderable = to_renderable(obj)
        assert isinstance(renderable, HTML)
        assert renderable.content == "<p>Inner HTML</p>"

    def test_mime_method_priority(self):
        """Test that _mime_() method takes priority over IPython methods."""

        class TestObject:
            def _mime_(self):
                return ("text/html", "<div>MIME HTML</div>")

            def _repr_html_(self):
                return "<p>HTML Repr</p>"

        obj = TestObject()
        renderable = to_renderable(obj)
        assert isinstance(renderable, HTML)
        assert renderable.content == "<div>MIME HTML</div>"

    def test_ipython_repr_fallback(self):
        """Test fallback to IPython _repr_*_ methods."""

        class TestObject:
            def _repr_html_(self):
                return "<p>HTML Repr</p>"

        obj = TestObject()
        renderable = to_renderable(obj)
        assert isinstance(renderable, HTML)
        assert renderable.content == "<p>HTML Repr</p>"

    def test_builtin_types_fallback(self):
        """Test fallback to built-in type handling."""
        from src.plaque.display import pd

        df = pd.DataFrame()
        df.to_html.return_value = "<table>...</table>"
        renderable = to_renderable(df)
        assert isinstance(renderable, HTML)
        assert renderable.content == "<table>...</table>"

    def test_repr_fallback(self):
        """Test final fallback to repr()."""

        class SimpleObject:
            def __repr__(self):
                return "SimpleObject(42)"

        obj = SimpleObject()
        renderable = to_renderable(obj)
        assert isinstance(renderable, Text)
        assert renderable.content == "SimpleObject(42)"

    def test_recursion_limit(self):
        """Test that infinite recursion is caught."""

        class RecursiveObject:
            def _display_(self):
                return self

        obj = RecursiveObject()
        renderable = to_renderable(obj)
        assert isinstance(renderable, Text)
        assert "Maximum display recursion depth exceeded" in renderable.content


class TestMimeMethod:
    """Test _mime_() method handling."""

    def test_mime_text_html(self):
        class TestObject:
            def _mime_(self):
                return ("text/html", "<b>Bold text</b>")

        renderable = to_renderable(TestObject())
        assert isinstance(renderable, HTML)
        assert renderable.content == "<b>Bold text</b>"

    def test_mime_image_png(self):
        test_data = base64.b64encode(b"png_data").decode()

        class TestObject:
            def _mime_(self):
                return ("image/png", test_data)

        renderable = to_renderable(TestObject())
        assert isinstance(renderable, PNG)
        assert renderable.content == b"png_data"


class TestIpythonReprMethods:
    """Test IPython _repr_*_ method handling."""

    def test_repr_html_priority(self):
        class TestObject:
            def _repr_html_(self):
                return "<p>HTML</p>"

            def _repr_svg_(self):
                return "<svg>...</svg>"

        renderable = to_renderable(TestObject())
        assert isinstance(renderable, HTML)
        assert renderable.content == "<p>HTML</p>"

    def test_repr_svg(self):
        class TestObject:
            def _repr_svg_(self):
                return "<svg>...</svg>"

        renderable = to_renderable(TestObject())
        assert isinstance(renderable, SVG)
        assert renderable.content == "<svg>...</svg>"

    def test_repr_png_bytes(self):
        class TestObject:
            def _repr_png_(self):
                return b"png_bytes"

        renderable = to_renderable(TestObject())
        assert isinstance(renderable, PNG)
        assert renderable.content == b"png_bytes"

    def test_repr_jpeg_b64_string(self):
        jpeg_b64 = base64.b64encode(b"jpeg_data").decode()

        class TestObject:
            def _repr_jpeg_(self):
                return jpeg_b64

        renderable = to_renderable(TestObject())
        assert isinstance(renderable, JPEG)
        assert renderable.content == b"jpeg_data"

    def test_repr_markdown(self):
        class TestObject:
            def _repr_markdown_(self):
                return "# Header"

        renderable = to_renderable(TestObject())
        assert isinstance(renderable, Markdown)
        assert renderable.content == "# Header"

    def test_repr_latex(self):
        class TestObject:
            def _repr_latex_(self):
                return "E=mc^2"

        renderable = to_renderable(TestObject())
        assert isinstance(renderable, Latex)
        assert renderable.content == "E=mc^2"

    def test_repr_json(self):
        class TestObject:
            def _repr_json_(self):
                return {"key": "value"}

        renderable = to_renderable(TestObject())
        assert isinstance(renderable, JSON)
        assert renderable.content == {"key": "value"}


class TestBuiltinTypes:
    """Test built-in type handling."""

    def test_matplotlib_figure(self):
        from src.plaque.display import matplotlib

        fig = matplotlib.figure.Figure()
        renderable = to_renderable(fig)
        assert isinstance(renderable, PNG)
        # Check that savefig was called on the mock object
        fig.savefig.assert_called_once()

    def test_pandas_dataframe(self):
        from src.plaque.display import pd

        df = pd.DataFrame()
        df.to_html.return_value = "<table>...</table>"
        renderable = to_renderable(df)
        assert isinstance(renderable, HTML)
        assert renderable.content == "<table>...</table>"
        df.to_html.assert_called_once()

    def test_pil_image(self):
        from src.plaque.display import Image

        img = Image.Image()
        renderable = to_renderable(img)
        assert isinstance(renderable, PNG)
        img.save.assert_called_once()
