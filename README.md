# document-normalizer

[![Apri in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Sica997rius/Document-normalizer/blob/main/document_normalizer_colab.ipynb)

**Provalo su Google Colab:** apri il link qui sopra e scegli *Runtime → Esegui tutto*. Non serve installare niente né avere un account GitHub.

Programma da riga di comando che **pulisce e ordina i file di testo di una cartella** (`.txt`, `.md`, `.csv`), propone un nome file ordinato, trova la data, crea un breve estratto di ogni file e **registra ogni esecuzione in uno storico JSON**.

Prima di toccare i file chiede **una sola conferma**: se rispondi "no", sul disco non cambia nulla.
Alla fine puoi **cercare una parola tra i titoli** della sessione appena salvata.

Scritto in Python, usa **solo la libreria standard**: non servono pacchetti esterni.

---

## Cosa fa, in breve

Per ogni file della cartella (e delle sottocartelle):

| | File `.txt` e `.md` | File `.csv` |
|---|---|---|
| **Pulizia del testo** | spazi e tab doppi, righe vuote in eccesso, a capo di Windows, caratteri invisibili | uguale, ma **i tab restano** (in un CSV separano le colonne) |
| **Nuovo nome** | maiuscole e spazi: `nota_riunione.txt` → `Nota Riunione.txt` | il nome resta quello, solo ripulito: `report  mese.csv` → `report mese.csv` |
| **Data** | la prima data valida **nel testo** | solo se è **nel nome del file** |
| **Estratto** | i primi 160 caratteri | la prima riga, una coppia `colonna: valore` per riga |

Altre regole:

- **File binari** (immagini, archivi… salvati con estensione `.txt`): estratto `FILE BINARIO NON LEGIBILE.`; il contenuto non viene mai modificato.
- **Caratteri stranieri o non previsti** (cinese, emoji, `<`, `{`…): all'estratto si aggiunge `(alcuni caratteri non sono legibili o sono relativi ad altre lingue straniere)`.
- **File salvati con il Blocco note di Windows** (codifica cp1252) e **UTF-16**: letti correttamente, senza perdere gli accenti.
- **Date**: riconosce `2024-03-15`, `15/03/2024`, `15.03.2024`, `15-03-2024`; scarta le date impossibili (`31/02/2024`); segnala come `uncertain format` quelle che si potrebbero leggere al contrario (`05/06/2024`).
- **Nomi già occupati**: se il nuovo nome esiste già, usa `Nome (2).txt`, `Nome (3).txt`…
- **File vuoti** saltati, **collegamenti simbolici** ignorati, **altre estensioni** elencate ma non toccate.

---

## Requisiti

- **Python 3.9 o più recente** ([python.org](https://www.python.org/downloads/))
- **Git**, solo per scaricare il progetto con `git clone` (in alternativa: *Code → Download ZIP* su GitHub)

---

## Installazione

Il progetto si installa in un **ambiente virtuale**: una cartella `.venv` che contiene una copia di Python riservata a questo progetto, così non tocchi il Python del sistema.

### 1. Scarica il progetto

```bash
git clone https://github.com/Sica997rius/document-normalizer.git
cd document-normalizer
```

### 2. Crea e attiva l'ambiente virtuale

**Windows (PowerShell o Prompt dei comandi)**

```bat
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Quando l'ambiente è attivo, all'inizio della riga del terminale compare `(.venv)`.

> Su Windows, se PowerShell blocca l'attivazione con un errore sugli "script", esegui una volta
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e riprova.

### 3. Installa

```bash
pip install -r requirements.txt   # strumenti per i test (pytest)
pip install -e .                  # il programma e il comando document-normalizer
```

`-e` ("editable") collega l'installazione alla cartella del progetto: se modifichi il codice, la modifica vale subito, senza reinstallare.

Verifica:

```bash
document-normalizer --version
```

---

## Esecuzione

```bash
document-normalizer                          # ti chiede quale cartella analizzare
document-normalizer percorso/della/cartella  # cartella indicata direttamente
python -m document_normalizer                # alternativa senza il comando installato
document-normalizer --help                   # tutte le opzioni
```

Opzioni:

| Opzione | Significato |
|---|---|
| `cartella` | cartella da analizzare (se manca, viene chiesta) |
| `--session-file FILE` | file storico da usare (predefinito: `session.json` nella cartella da cui lanci il comando) |
| `--version` | mostra la versione |

### Cosa succede durante un'esecuzione

1. Il programma elenca i file trovati, divisi in ammessi (testo, dati, markdown) e non ammessi.
2. Analizza ogni file e mostra titolo, numero di parole, data, codifica, estratto e modifiche proposte. **In questa fase non scrive nulla.**
3. Alla fine mostra l'elenco delle modifiche e chiede **una volta sola**:
   ```
   Do you want to save ALL these changes to disk? (y/n):
   ```
   - `y` (oppure `s`, `si`): riscrive i testi e rinomina i file;
   - `n`: non tocca niente.
4. Aggiunge la sessione allo storico `session.json`.
5. Chiede se vuoi **cercare una parola nei titoli della sessione appena salvata**. Scrivi una parola alla volta; premi solo Invio per finire.
   La ricerca ignora maiuscole e minuscole (`nota`, `NOTA` e `Nota` danno lo stesso risultato) e trova la parola anche dentro il titolo (`verb` trova `2024-03-15 Verbale`):
   ```
   Do you want to search a word in the titles of session 1? (y/n): y

   Word to search (press Enter to finish): NOTA
   1 title(s) contain 'NOTA':
     - Nota Sporca  ->  file_di_prova/Nota Sporca.txt

   Word to search (press Enter to finish):
   ```
   Se non hai salvato le modifiche, accanto al titolo compare `(not saved)`: il titolo è quello proposto, ma il file ha ancora il nome vecchio.

---

## Prova con l'archivio di esempio

In `sample_data/file_di_prova.zip` ci sono 15 file scelti per mettere alla prova tutte le regole: testo sporco, file già pulito, file di Windows, UTF-16, finto binario, caratteri cinesi ed emoji, data nel nome, nome fatto solo di `_`, file vuoto, CSV con punto e virgola, con virgolette e a capo, senza intestazione, separato da tab, un `.png` e una data impossibile in una sottocartella.

**Lavora sempre su una copia**: rispondendo `y` i file vengono modificati davvero.

```bash
# macOS / Linux
unzip sample_data/file_di_prova.zip
document-normalizer file_di_prova
```

```powershell
# Windows (PowerShell)
Expand-Archive sample_data\file_di_prova.zip -DestinationPath .
document-normalizer file_di_prova
```

Esempio di output per un CSV:

```
Document ID 3 (vendite_15-03-2024.csv) processed successfully:
  Title: vendite_15-03-2024
  Words: 12
  Date found: 2024-03-15
  Encoding: utf-8
  Excerpt:
    cliente: Rossi
    città: Torino
    importo: 1.250,50
  Changes: Changes made: text was normalized
```

Per rifare la prova da capo, cancella la cartella `file_di_prova` e `session.json` ed estrai di nuovo l'archivio.

---

## Lo storico `session.json`

Ogni esecuzione aggiunge una sessione. Ogni file ha come **chiave il suo percorso completo originale** (due file con lo stesso nome in cartelle diverse restano distinti):

```json
[
  {
    "session_id": 1,
    "session_date": "2026-10-12T00:45:10.123456",
    "documents": {
      "/home/utente/file_di_prova/nota_sporca.txt": {
        "file_name": "nota_sporca.txt",
        "title": "Nota Sporca",
        "original_path": "/home/utente/file_di_prova/nota_sporca.txt",
        "new_path": "/home/utente/file_di_prova/Nota Sporca.txt",
        "changes": ["Changes made: title was changed, text was normalized"],
        "saved": true
      }
    }
  }
]
```

- `saved`: `true` se le modifiche sono state scritte sul disco.
- `new_path`: il **nuovo** percorso se hai salvato, altrimenti **quello vecchio**.

---

## Struttura del progetto

```
document-normalizer/
├── document_normalizer/        il pacchetto Python
│   ├── __init__.py             versione ed elementi principali esportati
│   ├── __main__.py             permette "python -m document_normalizer"
│   ├── cli.py                  il programma interattivo (funzione main)
│   ├── config.py               impostazioni: estensioni, regole, testi, limiti
│   ├── models.py               classi Document e Session
│   ├── folder_reader.py        lettura cartella, lettura sicura, regole TXT/MD
│   ├── csv_reader.py           regole solo per i CSV
│   └── session_store.py        lettura, scrittura e ricerca nei titoli di session.json
├── tests/                      test automatici (pytest)
├── sample_data/
│   └── file_di_prova.zip       archivio di prova con 15 casi
├── pyproject.toml              configurazione del pacchetto e del comando
├── requirements.txt            dipendenze per i test
├── LICENSE
└── README.md
```

Le impostazioni modificabili (lunghezza dell'estratto, caratteri considerati leggibili, colonne mostrate nei CSV, testi delle note…) sono tutte in `config.py`.

---

## Test

Con l'ambiente virtuale attivo, dalla cartella del progetto:

```bash
python -m pytest
```

I test controllano le singole regole (pulizia, date, titoli, codifiche, CSV, ricerca) e l'intero programma sull'archivio di prova, rispondendo sia `y` sia `n`.

---

## Uso da Google Colab

```python
!git clone https://github.com/Sica997rius/document-normalizer.git
%cd document-normalizer
!pip install -q -e .
!unzip -q -o sample_data/file_di_prova.zip
```

Poi, in una nuova cella:

```python
from document_normalizer.cli import main
main(["file_di_prova"])
```

Colab chiede le risposte (Invio per iniziare, poi `y` o `n`) nella casella che compare sotto la cella.
Se hai modificato il codice, riavvia la sessione (*Runtime → Riavvia sessione*) prima di rieseguire: Colab tiene in memoria la versione già importata.

---

## Licenza

[MIT](LICENSE)
