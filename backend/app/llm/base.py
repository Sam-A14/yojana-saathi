"""The one interface the rest of the app uses to talk to a language model.

Why an interface: the extractor must not know which company's model it is using. Switching from
Gemini to Claude later means writing one new class here, not touching the pipeline.

The LLM only ever extracts rules from text and writes explanations. It never decides eligibility
(CLAUDE.md rule 1); that stays in app/rules/.
"""

from abc import ABC, abstractmethod


class LLMError(Exception):
    """The model could not be reached or refused. Never contains the API key."""


class LLMClient(ABC):
    # Stored with every proposal, so a bad batch can be traced back to the model that wrote it.
    model: str

    @abstractmethod
    def complete_json(self, *, system: str, prompt: str, temperature: float) -> str:
        """Ask for a JSON answer and return the model's raw text, exactly as received.

        Raw text on purpose, not a parsed dict: if the model returns broken JSON we must still be
        able to keep it and flag it, instead of losing it inside a parser error.
        """
