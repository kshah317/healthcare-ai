# summarizer.py
#
# the part that writes the summaries. HFSummarizer runs a small open model (qwen2.5-0.5b-instruct)
# with hugging face transformers. MockSummarizer is a stand-in for offline tests so the rest of
# the pipeline can be checked without a gpu. mock output is never reported as a model result.

PROMPT = (
    "Summarize this clinical note in two or three short sentences. "
    "Only use facts that are written in the note.\n\nNote:\n{note}"
)


class HFSummarizer:
    def __init__(self, model_name="Qwen/Qwen2.5-0.5B-Instruct", max_new_tokens=120):
        # imported here so the tests do not need torch installed
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.max_new_tokens = max_new_tokens

        # use the gpu in half precision when there is one, otherwise cpu in full precision
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype).to(self.device)
        self.model.eval()

    def summarize(self, note_text):
        messages = [{"role": "user", "content": PROMPT.format(note=note_text)}]
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        # greedy decoding so a rerun gives the same summary
        with self.torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=False)
        new_tokens = out[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


class MockSummarizer:
    # returns the faithful summary, and adds an invented drug to every fourth note
    def __init__(self, notes):
        from notes import gold_summary
        self.by_text = {n["text"]: n for n in notes}
        self.gold = gold_summary
        self.count = 0

    def summarize(self, note_text):
        summary = self.gold(self.by_text[note_text])
        self.count += 1
        if self.count % 4 == 0:
            summary += " Also takes warfarin 5 mg."
        return summary
