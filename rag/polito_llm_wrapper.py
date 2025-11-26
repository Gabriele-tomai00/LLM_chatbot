from typing import Any
import requests
from llama_index.core.llms import CustomLLM, CompletionResponse, CompletionResponseGen, LLMMetadata
from llama_index.core.llms.callbacks import llm_completion_callback
from pydantic import BaseModel, PrivateAttr
from pydantic import PrivateAttr
from dotenv import load_dotenv
import os

class PolitoLLMwrapper(CustomLLM):
    context_window: int = 3900
    num_output: int = 256
    model_name: str = "vllm_remote"

    # private attributes won't be copied by pydantic deepcopy
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
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.num_output,
        }
        response = requests.post(self._api_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        # estrai il contenuto principale
        text = data["choices"][0]["message"]["content"]
        
        # pulizia semplice: rimuove backticks multipli e newline iniziali/finali
        text = text.replace("```", "").strip()
        
        return text

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        text = self._call_api(prompt)
        return CompletionResponse(text=text)

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        text = self._call_api(prompt)
        # simulazione streaming, ma restituisce comunque testo coerente
        yield CompletionResponse(text=text, delta=text)
