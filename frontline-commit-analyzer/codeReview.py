import openai
import tiktoken
import os

class CodeReviewProvider:
    def __init__(self):
        openai.api_key = os.environ.get("OPENAI_API_TOKEN")
        with open("preprompt.txt", "r") as file:
            self.prepromt = file.read()
        
        with open("binary-answer-preprompt.txt", "r") as file:
            self.binary_prepromt = file.read()

    def get_bot_answer(self, prepromt, code):
        model_engine = "text-davinci-003"
        prompt = f"{prepromt}\n{code}"
        encoding = tiktoken.get_encoding("p50k_base")
        max_tokens = 4097 - len(encoding.encode(prompt))
        if max_tokens < 0:
            max_tokens = 4097
        completion = openai.Completion.create(
            engine=model_engine,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.5,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return completion.choices[0].text.strip()
    
    def get_code_review(self, code):
        return self.get_bot_answer(self.prepromt, code)
    
    def get_binary_answer(self, code):
        return self.get_bot_answer(self.binary_prepromt, code)
    
def main():
    codes = []
    with open("code-sample.txt", "r") as file:
        codes = file.readlines()

    code_review = CodeReviewProvider()
    for code in codes:
        print(code_review.get_code_review(code))
        print(f"Attention: {code_review.get_binary_answer(code)}")
        print("---------------")
if __name__ == "__main__":
    main()