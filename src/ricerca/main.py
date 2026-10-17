from .models import *


#Change(fix: session.json is saved in the analyzed folder, so the folder is now a parameter)
def load_history(folder="."):
  session_path = Path(folder) / SESSION_FILE
  try:
    with open(session_path, 'r', encoding="utf-8") as file:
      full_history = json.load(file)
      if not isinstance(full_history, list):
        full_history = [full_history]
      return full_history
  except FileNotFoundError:
    print(f"The file '{session_path}' does not exist yet.")
  except json.JSONDecodeError:
    print(f"The file '{session_path}' is not valid and cannot be read.")
  return []


def search_documents(full_history, search_words):
  results = []
  for session in full_history:
    for doc_data in session.get("documents", {}).values():
      # "date" and "excerpt" are found only if they are saved in session.json
      searchable_text = " ".join([
          doc_data.get("title") or "",
          doc_data.get("file_name") or "",
          doc_data.get("excerpt") or doc_data.get("Excerpt") or "",
          doc_data.get("original_path") or "",
          doc_data.get("new_path") or "",
          " ".join(doc_data.get("changes") or []),
          doc_data.get("date") or "",
      ]).lower()
      if all(word in searchable_text for word in search_words):
        results.append((session, doc_data))
  return results


def print_results(results):
  if not results:
    print("No document found with those words.\n")
    return
  print(f"\nDocuments found: {len(results)}\n")
  for session, doc_data in results:
    print(f"Session {session.get('session_id')} ({session.get('session_date')})")
    print(f"  Title: {doc_data.get('title')}")
    print(f"  Original name: {doc_data.get('file_name')}")
    print(f"  Original path: {doc_data.get('original_path')}")
    print(f"  Current path: {doc_data.get('new_path')}")
    print(f"  Changes: {', '.join(doc_data.get('changes') or [])}")
    print(f"  Date: {doc_data.get('date')}")
    print(f"  Excerpt: {doc_data.get('excerpt') or doc_data.get('Excerpt')}")
    print("-" * 40)
  print("")


def main():
  folder = input("Which analyzed folder do you want to search? (Enter = current folder) ").strip()
  full_history = load_history(folder or ".")
  if not full_history:
    return

  while True:
    search = input("Type words to search a document (or press Enter to exit): ").strip().lower()
    if not search:
      print("Search ended.")
      break
    results = search_documents(full_history, search.split())
    print_results(results)


if __name__ == "__main__":
  main()