from app.services.claim_extractor import extract_claims

text = """
The Earth revolves around the Sun.
Water boils at 100 degrees Celsius.
I love playing football.
India became independent in 1947.
"""

print(extract_claims(text))