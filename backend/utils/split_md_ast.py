"""
@version: python3.9
@author: hcb
@software: PyCharm
@file: split_md_ast.py
@time: 2025/11/3 11:22
"""
import mistletoe
import re
import mistletoe.markdown_renderer
import warnings

from typing import Any, Callable, List, Sequence, TYPE_CHECKING, ClassVar
from mistletoe.span_token import (
    SpanToken,
    RawText,
)
from mistletoe.block_token import (
    BlockToken,
    Table,
    TableRow,
    Heading,
    ThematicBreak,
    Document,
    Paragraph,
    List as ListBlock,
    HtmlBlock,
)
from llama_index.core.node_parser.interface import MetadataAwareTextSplitter
from llama_index.core.constants import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from llama_index.core.bridge.pydantic import Field, PrivateAttr

if TYPE_CHECKING:
    from bs4 import Tag

DEFAULT_METADATA_FORMAT_LEN = 2
DEFAULT_HTML_TAGS = [
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "b",
    "i",
    "u",
    "section",
]


class SplitException(Exception):
    pass


def _extract_text_from_tag(tag: "Tag") -> str:
    from bs4 import NavigableString

    texts = []
    for elem in tag.children:
        if isinstance(elem, NavigableString):
            if elem.strip():
                texts.append(elem.strip())
        elif elem.name in DEFAULT_HTML_TAGS:
            continue
        else:
            texts.append(elem.get_text().strip())
    return "\n".join(texts)


def _get_splits_from_html(html: str) -> List[str]:
    """Get nodes from document."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("bs4 is required to read HTML files.")

    soup = BeautifulSoup(html, "html.parser")
    html_nodes = []
    last_tag = None
    current_section = ""

    tags = soup.find_all(DEFAULT_HTML_TAGS)
    for tag in tags:
        tag_text = _extract_text_from_tag(tag)
        if tag.name == last_tag or last_tag is None:
            last_tag = tag.name
            current_section += f"{tag_text.strip()}\n"
        else:
            html_nodes.append(current_section.strip())
            last_tag = tag.name
            current_section = f"{tag_text}\n"

    if current_section:
        html_nodes.append(current_section.strip())

    return html_nodes


def _gen_table_header(size: int) -> List[str]:
    """generate a list of A B C D ... AA AB for table header"""
    headers = []
    for i in range(size):
        if i < 26:
            headers.append(chr(ord("A") + i))
        else:
            headers.append(f"{chr(ord('A') + i // 26 - 1)}{chr(ord('A') + i % 26)}")

    return [f"C_{x}" for x in headers]


class AstMarkdownSplitter(MetadataAwareTextSplitter):
    chunk_size: int = Field(
        default=DEFAULT_CHUNK_SIZE,
        description="The token chunk size for each chunk.",
        gt=0,
    )
    convert_table_ratio: float = Field(
        default=0.5,
        description="The ratio of the max_chunk_size to convert table to paragraph.",
        gt=0,
    )
    enable_first_line_as_title: bool = Field(
        default=True,
        description="Whether to enable the first line as title.",
    )

    # 添加类型注解，声明为类变量（非模型字段）
    SEPS: ClassVar[List[str]] = [".", "。", "！", "？", " "]  # 关键修改

    _tokenizer: Callable[[str], Sequence] = PrivateAttr()
    _renderer: mistletoe.markdown_renderer.MarkdownRenderer = PrivateAttr()

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        tokenizer: Callable[[str], Sequence] = None,
        *args: Any,
        **kwargs: Any,
    ):
        if chunk_overlap > chunk_size:
            raise ValueError(
                f"Got a larger chunk overlap ({chunk_overlap}) than chunk size "
                f"({chunk_size}), should be smaller."
            )
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            *args,
            **kwargs,
        )

        if tokenizer:
            self._tokenizer = tokenizer
        else:
            self._tokenizer = lambda x: x

    def split_text_metadata_aware(self, text: str, metadata_str: str) -> List[str]:
        metadata_len = len(self._tokenizer(metadata_str)) + DEFAULT_METADATA_FORMAT_LEN

        effective_chunk_size = self.chunk_size - metadata_len
        if effective_chunk_size <= 0:
            raise ValueError(
                f"Metadata length ({metadata_len}) is longer than chunk size "
                f"({self.chunk_size}). Consider increasing the chunk size or "
                "decreasing the size of your metadata to avoid this."
            )
        elif effective_chunk_size < 50:
            print(
                f"Metadata length ({metadata_len}) is close to chunk size "
                f"({self.chunk_size}). Resulting chunks are less than 50 tokens. "
                "Consider increasing the chunk size or decreasing the size of "
                "your metadata to avoid this.",
                flush=True,
            )

        return self._split_text(text, effective_chunk_size)

    def split_text(self, text: str) -> List[str]:
        return self._split_text(text, self.chunk_size)

    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        text = text.strip()

        with mistletoe.markdown_renderer.MarkdownRenderer() as self._renderer:
            doc = mistletoe.Document(text)

            if self.enable_first_line_as_title:
                # when paragraph is the first block, convert it to heading
                if isinstance(doc.children[0], Paragraph):
                    first_block = doc.children[0]
                    heading = Heading((1, "", ""))
                    heading.children = first_block.children
                    doc.children[0] = heading

            return self._split_document(doc, chunk_size)

    def _tik_block_token(self, block: BlockToken) -> List[str]:
        s = self._render_block(block)
        return s, len(self._tokenizer(s))

    def _render_block(self, token: BlockToken) -> str:
        s = "\n".join(
            self._renderer.render_map[token.__class__.__name__](
                token, max_line_length=None
            )
        )

        if isinstance(token, Table):
            # replace multiple spaces with single space
            s = re.sub(r"\ +", " ", s)
            # replace | --- | with | - | to reduce the size
            s = re.sub(r"(-+)|(\| -+ \|)", lambda x: "-" if x.group(1) else "| - |", s)

        return s

    def _is_empty(self, token: BlockToken) -> bool:
        if isinstance(token, ThematicBreak):
            return True
        return len(token.children) == 0

    def _duplicate_block(self, block: BlockToken) -> BlockToken:
        s = self._render_block(block)
        doc = Document(s)
        return doc.children[0]

    def _split_paragraph(self, block: Paragraph, max_chunk_size: int):
        text = self._render_block(block)

        sentences = [[]]
        for char in text:
            sentences[-1].append(char)
            if char in self.SEPS:
                sentences.append([])

        sentences = ["".join(sentence) for sentence in sentences if len(sentence) > 0]
        tokens = [len(self._tokenizer(sentence)) for sentence in sentences]

        # split into 2 chunks
        split_idx = 0
        total_size = 0
        for i in range(len(sentences)):
            if total_size + tokens[i] > max_chunk_size:
                break
            split_idx = i

        if split_idx == 0:
            pair = [sentences[0], "".join(sentences[1:])]

        pair = [
            "".join(sentences[:split_idx]),
            "".join(sentences[split_idx:]),  # noqa
        ]
        return [Document(p).children[0] for p in pair if len(p) > 0]

    def _split_html(self, html: HtmlBlock, max_chunk_size: int) -> List[BlockToken]:
        html_nodes = _get_splits_from_html(html.content)
        if html_nodes:
            return [child for node in html_nodes for child in Document(node).children]
        return []

    def _get_raw_text(self, tokens: List[SpanToken]) -> str:
        s = ""

        for token in tokens:
            if isinstance(token, RawText):
                s += token.content

            if hasattr(token, "children"):
                s += self._get_raw_text(token.children)

        return s

    def _convert_table_to_paragraph(self, table: Table) -> List[BlockToken]:
        headers = []
        for table_cell in table.header.children:
            headers.append(table_cell.children)

        doc = Document("\n\n".join(["foo"] * len(table.children)))
        kv_sep = RawText(": ")
        cell_sep = RawText("\t")

        paragraphs = [x for x in doc.children if isinstance(x, Paragraph)]
        for table_row, paragraph in zip(table.children, paragraphs):
            children = []
            for header, table_cell in zip(headers, table_row.children):
                children += header + [kv_sep] + table_cell.children
                children += [cell_sep]
            children.pop()
            paragraph.children = children

        return doc.children

    def _count_token_table_row(self, table_row: Table) -> int:
        row_size = 2  # for the `| `
        for cell in table_row.children:
            cell_content = self._get_raw_text(cell.children)
            row_size += len(self._tokenizer(cell_content))
            row_size += 2  # for the ` | `
        row_size -= 1  # remove the last space ` `
        return row_size

    def _split_table(self, table: Table, max_chunk_size: int) -> List[BlockToken]:
        table_header_size = self._count_token_table_row(table.header)
        table_row_sizes = [self._count_token_table_row(row) for row in table.children]

        # if table header much larger, treat it as a table row not a header
        # replacing with A B C D ... as table header
        mean_of_table_row_sizes = sum(table_row_sizes) / len(table_row_sizes)
        treat_as_header = table_header_size > mean_of_table_row_sizes * 2
        if treat_as_header:
            table.children.insert(0, table.header)
            cell_count = len(table.header.children)
            table.header = TableRow(
                f"| { ' | '.join(_gen_table_header(cell_count)) } |"
            )
            table_row_sizes.insert(0, table_header_size)

        # convert to paragraph block
        if max(table_row_sizes) >= self.chunk_size * self.convert_table_ratio:
            return self._convert_table_to_paragraph(table)

        backup_children = table.children
        table.children = []

        for i, child in enumerate(backup_children):
            table.children.append(child)
            if len(self._tokenizer(self._render_block(table))) > max_chunk_size:
                table.children.pop()
                break

        if len(table.children) == 0:
            table.children = backup_children
            return [table]

        rest_table = table
        table = self._duplicate_block(table)
        rest_table.children = backup_children[i:]
        return [table, rest_table]

    def _split_list(
        self, list_block: ListBlock, max_chunk_size: int
    ) -> List[BlockToken]:
        backup_children = list_block.children
        list_block.children = []

        for i, child in enumerate(backup_children):
            list_block.children.append(child)
            if len(self._tokenizer(self._render_block(list_block))) > max_chunk_size:
                list_block.children.pop()
                break

        if len(list_block.children) == 0:
            list_block.children = backup_children
            return [list_block]

        rest_list = list_block
        list_block = self._duplicate_block(list_block)
        rest_list.children = backup_children[i:]
        return [list_block, rest_list]

    def _split_block(self, block: BlockToken, max_chunk_size: int) -> List[BlockToken]:
        if isinstance(block, Paragraph):
            return self._split_paragraph(block, max_chunk_size)
        elif isinstance(block, Table):
            return self._split_table(block, max_chunk_size)
        elif isinstance(block, ListBlock):
            return self._split_list(block, max_chunk_size)
        elif isinstance(block, HtmlBlock):
            return self._split_html(block, max_chunk_size)

        raise ValueError(f"unsupported block {block}")

    def _split_document(
        self,
        doc: Document,
        max_chunk_size: int,
    ):
        chunks: List[str] = []

        headers = {}
        total_size = 0
        block_contents = []

        while len(doc.children) > 0:
            child = doc.children.pop(0)
            # print("child", child)
            # 如果是空 block，则跳过
            if self._is_empty(child):
                # print("empty child", child)
                continue

            # 计算 block 的大小
            block_content, block_size = self._tik_block_token(child)
            # print("block_content", block_content)

            # 处理 header  假设当前child的层级是2  要删除字典中大于2的层级
            if isinstance(child, Heading):
                # print("child is heading", block_content, child.level)
                headers[child.level] = (child, block_size)
                for i in range(child.level + 1, max(headers.keys()) + 1):
                    if i in headers:
                        del headers[i]

            # 可以放入当前 chunk
            if total_size + block_size <= max_chunk_size:
                block_contents.append(block_content)
                total_size += block_size + 2
                continue

            # 无法放入当前 chunk，但是可以放入下一个 chunk
            if block_size < max_chunk_size:
                header_size = (
                    sum([size for _, size in headers.values()]) + 2 * len(headers) + 2
                )
                if header_size + block_size <= max_chunk_size:
                    # flush the current chunk
                    chunks.append("\n\n".join(block_contents).strip())
                    block_contents = []
                    total_size = 0

                    # start a new chunk
                    blocks = [block for block, _ in headers.values()]
                    if not isinstance(child, Heading):
                        blocks.append(child)
                    doc.children = blocks + doc.children
                    continue

            # 无法放入当前 chunk，也无法放入下一个 chunk
            # 则需要切分当前 block
            blocks = self._split_block(child, max_chunk_size - total_size - 1)

            if len(blocks) == 1 and len(block_contents) > 0 and block_contents:
                chunks.append("\n\n".join(block_contents).strip())
                block_contents = []
                total_size = 0
            # dead loop, block can not be splitted in a new chunk
            elif len(blocks) == 1 and total_size == 0:
                # warning with block type
                warnings.warn(
                    f"Block {child.__class__.__name__} can not be splitted in a new chunk. Block size: {block_size}, Chunk size: {max_chunk_size}. Treat it as an oversize chunk.",
                )
                # TODO: fallback to text split
                chunks.append(block_content)
                blocks = []

            doc.children = blocks + doc.children

        # flush the last chunk
        if block_contents:
            chunks.append("\n\n".join(block_contents).strip())

        return chunks


if __name__ == '__main__':
    md_file = r"D:\python_project\UIAgent\src\jianli_judge\正样本\C00759290-朱女士-Java工程师-南京-YQD(J16591)-原始简历.pdf.md"
    split_md_ast = AstMarkdownSplitter()
    md_document = open(md_file, "r", encoding="utf-8").read()
    chunks = split_md_ast.split_text(md_document)

    doc = mistletoe.Document(md_document)
