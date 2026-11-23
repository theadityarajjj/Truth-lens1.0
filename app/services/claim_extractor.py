import spacy

nlp = spacy.load("en_core_web_sm")


def extract_claims(text):
    doc = nlp(text)

    claims = []

    for sentence in doc.sents:
        sentence_text = sentence.text.strip()

        if len(sentence_text.split()) >= 4:
            claims.append(sentence_text)

    return claims