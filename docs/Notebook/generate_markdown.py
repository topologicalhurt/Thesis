import re

from pathlib import Path
from collections.abc import Sequence
from IPython.display import display, Markdown
from pylatex import NoEscape, NewLine


class EqnFormatter:
    def __init__(self, eqns: Sequence[str | tuple], markdown: bool = False):
        self.raw_eqns = eqns
        self.markdown_enabled = markdown
        self.content = []
        self.sections = self._parse_sections(eqns)

    def _parse_sections(self, eqns: Sequence[str | tuple]):
        sections = []
        current_section_title = ''
        current_section_eqns = []
        in_math_block = False

        for item in eqns:
            if isinstance(item, tuple) and item[0] == '$$':
                # This is a section with a title
                if in_math_block: # End previous math block
                    sections.append({'title': current_section_title, 'eqns': current_section_eqns})
                    current_section_eqns = []
                current_section_title = item[1]
                in_math_block = True
            elif item == '$$':
                # This is a math block delimiter (start or end)
                if in_math_block: # End of a math block
                    sections.append({'title': current_section_title, 'eqns': current_section_eqns})
                    current_section_eqns = []
                    current_section_title = '' # Reset title for next block
                    in_math_block = False
                else: # Start of a math block without a title
                    current_section_title = ''
                    in_math_block = True
            elif in_math_block:
                current_section_eqns.append(item)

        # Add any remaining section if the last block wasn't closed by $
        if current_section_eqns:
            sections.append({'title': current_section_title, 'eqns': current_section_eqns})

        return sections

    @staticmethod
    def _replace_operatorname_macro(content_str: str):
        """
        Github complains about 'The following macros are not allowed: operatorname.'
        Not sure why that is, but this function mitigates that by wrapping in mathop & text
        instead of the operatorname macro's.
        """
        return re.sub(
            r'\\operatorname\{(.*?)\}',
            r'\\mathop{\\text{\1}}',
            content_str
        )

    def _add_section_title(self, title: str):
        if title:
            self.content.insert(0, f'# {title}\n')

    def _join_markdown(self):
        return '\n\n'.join(self.content)

    def display_equations(self, fp: Path = None, title: str = '') -> None:
        for section in self.sections:
            md_title = f"## {section['title']}\n\n" if self.markdown_enabled and section['title'] else ''

            latex_eqn_body_parts = []
            for item in section['eqns']:
                if isinstance(item, tuple) and item[0] is False:
                    # Handle pylatex objects specifically
                    if isinstance(item[1], NewLine):
                        latex_eqn_body_parts.append('\\newline\n\n')       # LaTeX newline command + spacing for readability
                    else:
                        latex_eqn_body_parts.append(str(item[1])) # For other strings/objects
                else:
                    if isinstance(item, NoEscape):
                        latex_eqn_body_parts.append(item.s)
                    else:
                        latex_eqn_body_parts.append(str(item))

            latex_eqn_body = ''.join(latex_eqn_body_parts)

            final_markdown = f'{md_title}$$\n{latex_eqn_body}\n$$'

            display(Markdown(final_markdown))
            self.content.append(final_markdown)

        if fp is not None:
            self._add_section_title(title)
            full_content_str = self._join_markdown()
            to_write = self._replace_operatorname_macro(full_content_str)

            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(to_write, encoding='utf-8')
