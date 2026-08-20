"""Upload a document into a session and ask questions about it."""

import sys
import tempfile

from _env import client

ge = client()

if len(sys.argv) > 1:
    path = sys.argv[1]
else:  # no file given: create a small demo memo
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, prefix="portfolio-memo-")
    tmp.write("ACME Corp Q2 loan portfolio memo.\n"
              "Total originations: $48M. Delinquency rate: 1.2%.\n"
              "Key risk: concentration in commercial real estate (34% of book).\n")
    tmp.close()
    path = tmp.name

up = ge.upload_file(path)  # session="-" -> creates the session too
print("uploaded:", up["fileName"], "fileId:", up["fileId"],
      "tokens:", up.get("tokenCount"))

result = ge.ask("What is the delinquency rate and the key risk in the attached memo?",
                session=up["session"], file_ids=[up["fileId"]])
print(result.text)
