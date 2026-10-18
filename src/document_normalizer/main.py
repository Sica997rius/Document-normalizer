from .models import *
from .readers import *


def main():
  start = input(
    "Before running the normalization, make sure that the files you intend to read\n"
    "in the folders and subfolders of the main folder have an allowed format "
    "(.TXT, .CSV, .MD).\n"
    "Type a character or press Enter to continue: "
)
  print("")
  print("")
  folder_path = FolderReader.choose_folder()
  document_list = FolderReader.open_document_list(folder_path) if folder_path else {}
  #Change(one file per line)
  print_file_list(document_list)
  print("")

  if document_list:
    # Extraction of allowed and disallowed extensions
    allowed_files = FolderReader.allowed_extensions(document_list)
    disallowed_files = FolderReader.disallowed_extensions(document_list)

    print("")
    print("The allowed files are the following: ")
    print("")
    print("Text files: ")
    txt_documents = FolderReader.txt_documents(allowed_files)
    print_file_list(txt_documents)
    print("")
    print("Data files: ")
    csv_documents = FolderReader.csv_documents(allowed_files)
    print_file_list(csv_documents)
    print("")
    print("Markdown files: ")
    md_documents = FolderReader.md_documents(allowed_files)
    print_file_list(md_documents)
    print("")
    print("The disallowed files are the following: ")
    print_file_list(disallowed_files)
    print("")
    print("--- Start of document processing and indexing --- ")
    print("")

    indexed_documents = {}
    saved_data = {}
    doc_history = {}
    session_documents = {}

    # ================= LOOP 1: TEXT FILES (.TXT) =================
    #Change(fix: the question is asked again until the answer is valid - before, any other answer left "save" unset and the program crashed)
    while True:
      save_session = input(
        "Do you want to save the all data together or each one separately?\n"
        "1) together\n"
        "2) separately\n"
      )
      risposta = save_session.strip().lower()
      if risposta in ['2) separately', '2 separately', '2', 'separately', ') separately']:
          save = True
          break
      elif risposta in ['1) together', '1 together', '1', 'together', ') together']:
          save = False
          break
      print("Invalid answer: type 1 (together) or 2 (separately).\n")
    if save==True:
      if txt_documents:
        print("=== Processing type: TXT (Text files) ===\n")
        for number, (file_name, ext) in txt_documents.items():
          file_path = document_list[number]
          try:
            #Change(fix 1+2+8: read_file replaces open(..., errors="ignore") - see FolderReader.read_file)
            raw_text, encoding, is_binary = FolderReader.read_file(file_path)
            if raw_text:
              if is_binary:
                normalized_text = raw_text
                word_count = 0
                excerpt = BINARY_FILE_NOTE
                detected_date = None
              else:
                normalized_text = FolderReader.normalize_text(raw_text)
                word_count = FolderReader.count_words(normalized_text)
                excerpt = FolderReader.create_excerpt(normalized_text)
                detected_date = FolderReader.find_date(normalized_text)
              title = FolderReader.title_from_filename(Path(file_name).stem)

              doc = Document(
                  document_id=str(number),
                  title=title,
                  original_title=file_name,
                  word_count=word_count,
                  excerpt=excerpt,
                  content=normalized_text,
                  format=ext,
                  path=str(file_path),
                  date=detected_date,
                  original_content=raw_text,
                  #Change(fix 1: the detected encoding is stored in "extra" and printed, so you know when a file was read as cp1252 - a rewrite saves it as UTF-8 with the accents preserved)
                  extra={"encoding": encoding}
              )

              indexed_documents[number] = doc
              print(f"Document ID {number} ({file_name}) processed successfully:")
              print(f"  Title: {doc.title}")
              print(f"  Words: {doc.word_count}")
              print(f"  Date found: {doc.date}")
              print(f"  Encoding: {encoding}")
              print(f"  Excerpt: {doc.excerpt}")

              changes_description = doc.changes_made
              new_path = file_path
              if changes_description != "No changes":
                answer = input(f"\nChanges were detected for {file_name} ({changes_description}). Do you want to apply them to the file on disk? (y/n): ")
                if answer.lower() in ['y', 'yes', 's', 'si', 'sì']:
                  if doc.text_changed:
                    #Change(fix: newline="\n" - in text mode Windows wrote "\r\n" back, so the next run found the file "changed" again)
                    with open(file_path, "w", encoding="utf-8", newline="\n") as f_out:
                      f_out.write(normalized_text)
                    print(f"Text of '{file_name}' normalized and rewritten successfully.")
                  if doc.title_changed:
                    #Change(fix 6: numbered name instead of skipping the rename when the name is taken - see FolderReader.unique_path)
                    new_path = FolderReader.unique_path(file_path.with_name(doc.title + ext), file_path)
                    file_path.rename(new_path)
                    doc.path = str(new_path)
                    if new_path.stem != doc.title:
                      print(f"File '{file_name}' renamed to '{new_path.name}' ('{doc.title + ext}' was already taken).")
                    else:
                      print(f"File '{file_name}' renamed to '{new_path.name}'.")
                  print("")
                else:
                  print(f"Changes for '{file_name}' not saved to disk.\n")
                  changes_description = "Changes detected but not applied"

              session_documents[str(file_path)] = {
                  "file_name": file_name,
                  "title": doc.title,
                  "original_path": str(file_path),
                  "new_path": str(new_path),
                  "changes": [changes_description],
                  "date": doc.date,
                  "excerpt": doc.excerpt
                  }
              print("-" * 40)
            else:
              print(f"File {file_name} is empty and will be skipped.\n")
          except Exception as e:
            print(f"Error while processing {file_name}: {e}\n")

      # ================= LOOP 2: MARKDOWN FILES (.MD) =================
      if md_documents:
        print("=== Processing type: MD (Markdown) ===\n")
        for number, (file_name, ext) in md_documents.items():
          file_path = document_list[number]
          try:
            #Change(fix 1+2+8: read_file, as in the TXT loop)
            raw_text, encoding, is_binary = FolderReader.read_file(file_path)
            if raw_text:
              if is_binary:
                normalized_text = raw_text
                word_count = 0
                excerpt = BINARY_FILE_NOTE
                detected_date = None
              else:
                normalized_text = FolderReader.normalize_text(raw_text)
                word_count = FolderReader.count_words(normalized_text)
                excerpt = FolderReader.create_excerpt(normalized_text)
                detected_date = FolderReader.find_date(normalized_text)
              title = FolderReader.title_from_filename(Path(file_name).stem)

              doc = Document(
                  document_id=str(number),
                  title=title,
                  original_title=file_name,
                  word_count=word_count,
                  excerpt=excerpt,
                  content=normalized_text,
                  format=ext,
                  path=str(file_path),
                  date=detected_date,
                  original_content=raw_text,
                  #Change(fix 1: encoding stored, as in the TXT loop)
                  extra={"encoding": encoding}
              )

              indexed_documents[number] = doc
              print(f"Document ID {number} ({file_name}) processed successfully:")
              print(f"  Title: {doc.title}")
              print(f"  Words: {doc.word_count}")
              print(f"  Date found: {doc.date}")
              print(f"  Encoding: {encoding}")
              print(f"  Excerpt: {doc.excerpt}")

              changes_description = doc.changes_made
              new_path = file_path
              if changes_description != "No changes":
                answer = input(f"\nChanges were detected for {file_name} ({changes_description}). Do you want to apply them to the file on disk? (y/n): ")
                if answer.lower() in ['y', 'yes', 's', 'si', 'sì']:
                  if doc.text_changed:
                    #Change(fix: newline="\n" - in text mode Windows wrote "\r\n" back, so the next run found the file "changed" again)
                    with open(file_path, "w", encoding="utf-8", newline="\n") as f_out:
                      f_out.write(normalized_text)
                    print(f"Text of '{file_name}' normalized and rewritten successfully.")
                  if doc.title_changed:
                    #Change(fix 6: numbered name instead of skipping the rename when the name is taken as in the TXT loop)
                    new_path = FolderReader.unique_path(file_path.with_name(doc.title + ext), file_path)
                    file_path.rename(new_path)
                    doc.path = str(new_path)
                    if new_path.stem != doc.title:
                      print(f"File '{file_name}' renamed to '{new_path.name}' ('{doc.title + ext}' was already taken).")
                    else:
                      print(f"File '{file_name}' renamed to '{new_path.name}'.")
                  print("")
                else:
                  print(f"Changes for '{file_name}' not saved to disk.\n")
                  changes_description = "Changes detected but not applied"

              session_documents[str(file_path)] = {
                  "file_name": file_name,
                  "title": doc.title,
                  "original_path": str(file_path),
                  "new_path": str(new_path),
                  "changes": [changes_description],
                  "date": doc.date,
                  "excerpt": doc.excerpt
                  }
              print("-" * 40)
            else:
              print(f"File {file_name} is empty and will be skipped.\n")
          except Exception as e:
            print(f"Error while processing {file_name}: {e}\n")

      # ================= LOOP 3: DATA FILES (.CSV) =================
      if csv_documents:
        print("=== Processing type: CSV (Data files) ===\n")
        for number, (file_name, ext) in csv_documents.items():
          file_path = document_list[number]
          try:
            #Change(fix 1+2+8: read_file, as in the TXT loop)
            raw_text, encoding, is_binary = FolderReader.read_file(file_path)
            if raw_text:
              if is_binary:
                normalized_text = raw_text
                word_count = 0
                excerpt = BINARY_FILE_NOTE
              else:
                normalized_text = CSVReader.normalize_text(raw_text)
                word_count = FolderReader.count_words(normalized_text)
                excerpt = CSVReader.create_excerpt(normalized_text)
              detected_date = CSVReader.date_from_title(Path(file_name).stem)
              title = CSVReader.title_from_existing(Path(file_name).stem)

              doc = Document(
                  document_id=str(number),
                  title=title,
                  original_title=file_name,
                  word_count=word_count,
                  excerpt=excerpt,
                  content=normalized_text,
                  format=ext,
                  path=str(file_path),
                  date=detected_date,
                  original_content=raw_text,
                  #Change(fix 1: encoding stored, as in the TXT loop)
                  extra={"encoding": encoding}
              )

              indexed_documents[number] = doc
              print(f"Document ID {number} ({file_name}) processed successfully:")
              print(f"  Title: {doc.title}")
              print(f"  Words: {doc.word_count}")
              print(f"  Date found: {doc.date}")
              print(f"  Encoding: {encoding}")
              print("  Excerpt:\n    " + doc.excerpt.replace("\n", "\n    "))

              changes_description = doc.changes_made
              new_path = file_path
              if changes_description != "No changes":
                answer = input(f"\nChanges were detected for {file_name} ({changes_description}). Do you want to apply them to the file on disk? (y/n): ")
                if answer.lower() in ['y', 'yes', 's', 'si', 'sì']:
                  if doc.text_changed:
                    #Change(fix: newline="\n" - in text mode Windows wrote "\r\n" back, so the next run found the file "changed" again)
                    with open(file_path, "w", encoding="utf-8", newline="\n") as f_out:
                      f_out.write(normalized_text)
                    print(f"Text of '{file_name}' normalized and rewritten successfully.")
                  if doc.title_changed:
                    #Change(fix 6: numbered name instead of skipping the rename when the name is taken as in the TXT loop)
                    new_path = FolderReader.unique_path(file_path.with_name(doc.title + ext), file_path)
                    file_path.rename(new_path)
                    doc.path = str(new_path)
                    if new_path.stem != doc.title:
                      print(f"File '{file_name}' renamed to '{new_path.name}' ('{doc.title + ext}' was already taken).")
                    else:
                      print(f"File '{file_name}' renamed to '{new_path.name}'.")
                  print("")
                else:
                  print(f"Changes for '{file_name}' not saved to disk.\n")
                  changes_description = "Changes detected but not applied"

              session_documents[str(file_path)] = {
                  "file_name": file_name,
                  "title": doc.title,
                  "original_path": str(file_path),
                  "new_path": str(new_path),
                  "changes": [changes_description],
                  "date": doc.date,
                  "excerpt": doc.excerpt.replace("\n", "   ")
                  }
              print("-" * 40)
            else:
              print(f"File {file_name} is empty and will be skipped.\n")
          except Exception as e:
            print(f"Error while processing {file_name}: {e}\n")

      # Outside the loops: handle the overall saving of the session to a JSON file
      if session_documents:
        try:
          #Change(fix: session.json is saved in the analyzed folder)
          session_path = folder_path / SESSION_FILE
          temp_session = Session(session_id=0, session_date=datetime.now(), history_path=str(session_path))
          new_session_id = temp_session.last_session_id + 1

          #Change(fix: session_record was never created in this branch, so saving failed with "name 'session_record' is not defined")
          session_record = Session(
              session_id=new_session_id,
              session_date=datetime.now(),
              documents=session_documents,
              history_path=str(session_path)
          )

          try:
            with open(session_path, 'r', encoding="utf-8") as file:
              full_history = json.load(file)
              if not isinstance(full_history, list):
                full_history = [full_history]
          except (FileNotFoundError, json.JSONDecodeError):
            full_history = []

          session_data = {
              "session_id": session_record.session_id,
              "session_date": session_record.session_date.isoformat(),
              "documents": session_record.documents
          }

          full_history.append(session_data)
          with open(session_path, 'w', encoding="utf-8") as file:
            json.dump(full_history, file, indent=2, ensure_ascii=False)

          print(f"\nSession {new_session_id} saved successfully to '{session_path}'.")
        except Exception as e:
          print(f"Error while saving the global session: {e}")
    
    
    
    
    if save==False:
      if txt_documents:
        print("=== Processing type: TXT (Text files) ===\n")
        for number, (file_name, ext) in txt_documents.items():
          file_path = document_list[number]
          try:
            #Change(fix 1+2+8: read_file replaces open(..., errors="ignore") - see FolderReader.read_file)
            raw_text, encoding, is_binary = FolderReader.read_file(file_path)
            if raw_text:
              if is_binary:
                normalized_text = raw_text
                word_count = 0
                excerpt = BINARY_FILE_NOTE
                detected_date = None
              else:
                normalized_text = FolderReader.normalize_text(raw_text)
                word_count = FolderReader.count_words(normalized_text)
                excerpt = FolderReader.create_excerpt(normalized_text)
                detected_date = FolderReader.find_date(normalized_text)
              title = FolderReader.title_from_filename(Path(file_name).stem)

              doc = Document(
                  document_id=str(number),
                  title=title,
                  original_title=file_name,
                  word_count=word_count,
                  excerpt=excerpt,
                  content=normalized_text,
                  format=ext,
                  path=str(file_path),
                  date=detected_date,
                  original_content=raw_text,
                  #Change(fix 1: the detected encoding is stored in "extra" and printed, so you know when a file was read as cp1252 - a rewrite saves it as UTF-8 with the accents preserved)
                  extra={"encoding": encoding}
              )

              indexed_documents[number] = doc
              print(f"Document ID {number} ({file_name}) processed successfully:")
              print(f"  Title: {doc.title}")
              print(f"  Words: {doc.word_count}")
              print(f"  Date found: {detected_date}")
              print(f"  Encoding: {encoding}")
              print(f"  Excerpt: {doc.excerpt}")

              changes_description = doc.changes_made
              new_path = file_path
              if doc.text_changed:
                #Change(fix: newline="\n" - in text mode Windows wrote "\r\n" back, so the next run found the file "changed" again)
                with open(file_path, "w", encoding="utf-8", newline="\n") as f_out:
                  f_out.write(normalized_text)
                print(f"Text of '{file_name}' normalized and rewritten successfully.")
              if doc.title_changed:
                #Change(fix 6: numbered name instead of skipping the rename when the name is taken - see FolderReader.unique_path)
                new_path = FolderReader.unique_path(file_path.with_name(doc.title + ext), file_path)
                file_path.rename(new_path)
                doc.path = str(new_path)
                if new_path.stem != doc.title:
                  print(f"File '{file_name}' renamed to '{new_path.name}' ('{doc.title + ext}' was already taken).")
                else:
                  print(f"File '{file_name}' renamed to '{new_path.name}'.")

              session_documents[str(file_path)] = {
                  "file_name": file_name,
                  "title": doc.title,
                  "original_path": str(file_path),
                  "new_path": str(new_path),
                  "changes": [changes_description],
                  "date": doc.date,
                  "excerpt": doc.excerpt
                  }
              print("-" * 40)
            else:
              print(f"File {file_name} is empty and will be skipped.\n")
          except Exception as e:
            print(f"Error while processing {file_name}: {e}\n")

      # ================= LOOP 2: MARKDOWN FILES (.MD) =================
      if md_documents:
        print("=== Processing type: MD (Markdown) ===\n")
        for number, (file_name, ext) in md_documents.items():
          file_path = document_list[number]
          try:
            #Change(fix 1+2+8: read_file, as in the TXT loop)
            raw_text, encoding, is_binary = FolderReader.read_file(file_path)
            if raw_text:
              if is_binary:
                normalized_text = raw_text
                word_count = 0
                excerpt = BINARY_FILE_NOTE
                detected_date = None
              else:
                normalized_text = FolderReader.normalize_text(raw_text)
                word_count = FolderReader.count_words(normalized_text)
                excerpt = FolderReader.create_excerpt(normalized_text)
                detected_date = FolderReader.find_date(normalized_text)
              title = FolderReader.title_from_filename(Path(file_name).stem)

              doc = Document(
                  document_id=str(number),
                  title=title,
                  original_title=file_name,
                  word_count=word_count,
                  excerpt=excerpt,
                  content=normalized_text,
                  format=ext,
                  path=str(file_path),
                  date=detected_date,
                  original_content=raw_text,
                  #Change(fix 1: encoding stored, as in the TXT loop)
                  extra={"encoding": encoding}
              )

              indexed_documents[number] = doc
              print(f"Document ID {number} ({file_name}) processed successfully:")
              print(f"  Title: {doc.title}")
              print(f"  Words: {doc.word_count}")
              print(f"  Date found: {doc.date}")
              print(f"  Encoding: {encoding}")
              print(f"  Excerpt: {doc.excerpt}")

              changes_description = doc.changes_made
              new_path = file_path
              if doc.text_changed:
                #Change(fix: newline="\n" - in text mode Windows wrote "\r\n" back, so the next run found the file "changed" again)
                with open(file_path, "w", encoding="utf-8", newline="\n") as f_out:
                  f_out.write(normalized_text)
                print(f"Text of '{file_name}' normalized and rewritten successfully.")
              if doc.title_changed:
                #Change(fix 6: numbered name instead of skipping the rename when the name is taken as in the TXT loop)
                new_path = FolderReader.unique_path(file_path.with_name(doc.title + ext), file_path)
                file_path.rename(new_path)
                doc.path = str(new_path)
                if new_path.stem != doc.title:
                  print(f"File '{file_name}' renamed to '{new_path.name}' ('{doc.title + ext}' was already taken).")
                else:
                  print(f"File '{file_name}' renamed to '{new_path.name}'.")
              session_documents[str(file_path)] = {
                  "file_name": file_name,
                  "title": doc.title,
                  "original_path": str(file_path),
                  "new_path": str(new_path),
                  "changes": [changes_description],
                  "date": doc.date,
                  "excerpt": doc.excerpt
                  }
              print("-" * 40)
            else:
              print(f"File {file_name} is empty and will be skipped.\n")
          except Exception as e:
            print(f"Error while processing {file_name}: {e}\n")

      # ================= LOOP 3: DATA FILES (.CSV) =================
      if csv_documents:
        print("=== Processing type: CSV (Data files) ===\n")
        for number, (file_name, ext) in csv_documents.items():
          file_path = document_list[number]
          try:
            #Change(fix 1+2+8: read_file, as in the TXT loop)
            raw_text, encoding, is_binary = FolderReader.read_file(file_path)
            if raw_text:
              if is_binary:
                normalized_text = raw_text
                word_count = 0
                excerpt = BINARY_FILE_NOTE
              else:
                normalized_text = CSVReader.normalize_text(raw_text)
                word_count = FolderReader.count_words(normalized_text)
                excerpt = CSVReader.create_excerpt(normalized_text)
              detected_date = CSVReader.date_from_title(Path(file_name).stem)
              title = CSVReader.title_from_existing(Path(file_name).stem)

              doc = Document(
                  document_id=str(number),
                  title=title,
                  original_title=file_name,
                  word_count=word_count,
                  excerpt=excerpt,
                  content=normalized_text,
                  format=ext,
                  path=str(file_path),
                  date=detected_date,
                  original_content=raw_text,
                  #Change(fix 1: encoding stored, as in the TXT loop)
                  extra={"encoding": encoding}
              )

              indexed_documents[number] = doc
              print(f"Document ID {number} ({file_name}) processed successfully:")
              print(f"  Title: {doc.title}")
              print(f"  Words: {doc.word_count}")
              print(f"  Date found: {doc.date}")
              print(f"  Encoding: {encoding}")
              print("  Excerpt:\n    " + doc.excerpt.replace("\n", "\n    "))

              changes_description = doc.changes_made
              new_path = file_path
              if doc.text_changed:
                #Change(fix: newline="\n" - in text mode Windows wrote "\r\n" back, so the next run found the file "changed" again)
                with open(file_path, "w", encoding="utf-8", newline="\n") as f_out:
                  f_out.write(normalized_text)
                print(f"Text of '{file_name}' normalized and rewritten successfully.")
              if doc.title_changed:
                #Change(fix 6: numbered name instead of skipping the rename when the name is taken as in the TXT loop)
                new_path = FolderReader.unique_path(file_path.with_name(doc.title + ext), file_path)
                file_path.rename(new_path)
                doc.path = str(new_path)
                if new_path.stem != doc.title:
                  print(f"File '{file_name}' renamed to '{new_path.name}' ('{doc.title + ext}' was already taken).")
                else:
                  print(f"File '{file_name}' renamed to '{new_path.name}'.")
              session_documents[str(file_path)] = {
                  "file_name": file_name,
                  "title": doc.title,
                  "original_path": str(file_path),
                  "new_path": str(new_path),
                  "changes": [changes_description],
                  "date": doc.date,
                  "excerpt": doc.excerpt.replace("\n", "   ")
                  }
              print("-" * 40)
            else:
              print(f"File {file_name} is empty and will be skipped.\n")
          except Exception as e:
            print(f"Error while processing {file_name}: {e}\n")

      # Outside the loops: handle the overall saving of the session to a JSON file
      if session_documents:
        try:
          #Change(fix: session.json is saved in the analyzed folder)
          session_path = folder_path / SESSION_FILE
          temp_session = Session(session_id=0, session_date=datetime.now(), history_path=str(session_path))
          new_session_id = temp_session.last_session_id + 1

          session_record = Session(
              session_id=new_session_id,
              session_date=datetime.now(),
              documents=session_documents,
              history_path=str(session_path)
          )

          try:
            with open(session_path, 'r', encoding="utf-8") as file:
              full_history = json.load(file)
              if not isinstance(full_history, list):
                full_history = [full_history]
          except (FileNotFoundError, json.JSONDecodeError):
            full_history = []

          session_data = {
              "session_id": session_record.session_id,
              "session_date": session_record.session_date.isoformat(),
              "documents": session_record.documents
          }

          full_history.append(session_data)
          with open(session_path, 'w', encoding="utf-8") as file:
            json.dump(full_history, file, indent=2, ensure_ascii=False)

          print(f"\nSession {new_session_id} saved successfully to '{session_path}'.")
        except Exception as e:
          print(f"Error while saving the global session: {e}")


if __name__ == "__main__":
  main()
