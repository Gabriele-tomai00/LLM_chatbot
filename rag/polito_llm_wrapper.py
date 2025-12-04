from typing import Any
import requests
from llama_index.core.llms import CustomLLM, CompletionResponse, CompletionResponseGen, LLMMetadata
from llama_index.core.llms.callbacks import llm_completion_callback
from pydantic import PrivateAttr
from dotenv import load_dotenv
import os
from typing import Any, ClassVar

system_prompt_path = os.path.join(os.path.dirname(__file__), "prompt_for_llm.txt")
with open(system_prompt_path, "r", encoding="utf-8") as f:
    SYSTEM_TEXT = f.read().strip()



class PolitoLLMwrapper(CustomLLM):
    context_window: int = 3900
    num_output: int = 1024
    model_name: str = "vllm_remote"

    SYSTEM: ClassVar[str] = SYSTEM_TEXT

    def __init__(self, **data):
        super().__init__(**data)
        dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
        load_dotenv(dotenv_path)
        self._bearer_token = os.getenv("BEARER_TOKEN")
        self._api_url = os.getenv("API_URL")
        self._model = os.getenv("MODEL")

        if not self._bearer_token or not self._api_url or not self._model:
            raise RuntimeError("Missing environment variables for LLM configuration.")


    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.num_output,
            model_name=self.model_name,
        )

    def _call_api(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self._bearer_token}",
            "Content-Type": "application/json"
        }

        full_prompt = (
            "<|system|>\n"
            + self.SYSTEM
            + "\n<|user|>\n"
            + prompt
            + "\n<|assistant|>\n"
        )

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": self.num_output,
        }

        response = requests.post(self._api_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    def _extract_answer(self, raw: str) -> str:
        # Remove debug sections
        cleaned = raw

        # Remove "Prompt:" blocks
        if "** Prompt:" in cleaned:
            cleaned = cleaned.split("** Prompt:", 1)[0]

        # Keep only last "ANSWER:" if present
        if "ANSWER:" in cleaned:
            cleaned = cleaned.split("ANSWER:", 1)[1]

        # Remove completion blocks
        if "** Completion:" in cleaned:
            cleaned = cleaned.split("** Completion:", 1)[-1]

        return cleaned.strip()

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        text = self._call_api(prompt)
        clean = self._extract_answer(text)
        return CompletionResponse(text=clean)

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        text = self._call_api(prompt)
        clean = self._extract_answer(text)
        for ch in clean:
            yield CompletionResponse(text=ch, delta=ch)