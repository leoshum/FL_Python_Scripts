import openai

def main():
    openai.api_key = "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"
    model_engine = "text-davinci-003"
    preprompt = ""
    with open("preprompt.txt", "r") as file:
        preprompt = file.read()

    code = ""
    with open("code-sample.txt", "r") as file:
        code = file.read()

    prompt = f"{preprompt}\n{code}"

    completion = openai.Completion.create(
        engine=model_engine,
        prompt=prompt,
        max_tokens=1024,
        temperature=0.5,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    print(completion.choices[0].text)

if __name__ == "__main__":
    main()