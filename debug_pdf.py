import pdfplumber

pdf_path = "M_T_Modulhandbuch.pdf"

with pdfplumber.open(pdf_path) as pdf:

    page_index = 10 
    if len(pdf.pages) > page_index:
        page = pdf.pages[page_index]
        text = page.extract_text()
        print(f"--- TESTO ESTRATTO DA PAGINA {page_index} ---")
        print(text)
        print("----------------------------------------------")
    else:
        print("Il PDF ha meno pagine del previsto.")