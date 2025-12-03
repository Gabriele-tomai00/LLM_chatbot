from typing import Any
import requests
from llama_index.core.llms import CustomLLM, CompletionResponse, CompletionResponseGen, LLMMetadata
from llama_index.core.llms.callbacks import llm_completion_callback
from pydantic import PrivateAttr
from dotenv import load_dotenv
import os
from typing import Any, ClassVar


class PolitoLLMwrapper(CustomLLM):
    context_window: int = 3900
    num_output: int = 1024
    model_name: str = "vllm_remote"

    SYSTEM: ClassVar[str] = (
    "Sei l’assistente ufficiale dell'Università di Trieste.\n"
    "Rispondi solo con informazioni basate sui documenti recuperati.\n"
    "Se non hai abbastanza informazioni, dillo chiaramente.\n"
    "Rispondi sempre in italiano."
    )


    load_dotenv()
    _bearer_token: str = PrivateAttr(os.getenv("BEARER_TOKEN"))
    _api_url: str = PrivateAttr(os.getenv("API_URL"))
    _model: str = PrivateAttr(os.getenv("MODEL"))

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
        key = "ANSWER:"
        if key in raw:
            return raw.split(key, 1)[1].strip()
        return raw.strip()

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