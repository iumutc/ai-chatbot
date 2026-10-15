import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


class LocalLLM:
    def __init__(self, model_id: str, device: str):
        self.model_id = model_id
        self.device = device

        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

        dtype = torch.float16 if device == "cuda" else torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=dtype,
            device_map="auto" if device == "cuda" else None,
            trust_remote_code=True,
        )
        self.model.eval()

        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

    def _to_input_ids(self, encoded):
        if isinstance(encoded, torch.Tensor):
            return encoded
        if isinstance(encoded, dict) and "input_ids" in encoded:
            return encoded["input_ids"]
        if hasattr(encoded, "input_ids"):
            return encoded.input_ids
        raise TypeError("Tokenizer output does not contain input_ids")

    def _build_inputs(self, system: str, user: str):
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        if getattr(self.tokenizer, "chat_template", None):
            encoded = self.tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
            )
            return self._to_input_ids(encoded)

        prompt = (
            f"System: {system.strip()}\n\n"
            f"User: {user.strip()}\n"
            "Assistant:"
        )
        encoded = self.tokenizer(prompt, return_tensors="pt")
        return self._to_input_ids(encoded)

    @torch.inference_mode()
    def generate(self, system: str, user: str, max_new_tokens: int = 256) -> str:
        input_ids = self._build_inputs(system, user).to(self.model.device)

        input_len = input_ids.shape[1]

        gen = self.model.generate(
            input_ids=input_ids,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
            repetition_penalty=1.05,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.pad_token_id,
            return_dict_in_generate=True,
        )

        seq = gen.sequences[0]
        new_tokens = seq[input_len:]

        answer = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        for bad in ["system\n", "user\n", "assistant\n", "Human:", "Assistant:"]:
            if bad in answer:
                answer = answer.replace(bad, "")

        return answer.strip()
