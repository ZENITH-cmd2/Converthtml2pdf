import asyncio
import base64
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    # Inizializza l'Actor di Apify
    async with Actor:
        Actor.log.info("Avvio dell'Actor HTML to PDF Converter...")
        
        # Recupera l'input passato da n8n
        actor_input = await Actor.get_input() or {}
        parameters = actor_input.get("Parameters", [])
        
        html_base64 = ""
        margins = {"top": "0", "right": "0", "bottom": "0", "left": "0"}
        page_size = "A4"
        
        # Parsing dell'input dinamico specificato da n8n
        for param in parameters:
            name = param.get("Name")
            if name == "File":
                file_value = param.get("FileValue", {})
                html_base64 = file_value.get("Data", "")
            elif name == "MarginLeft":
                margins["left"] = str(param.get("Value", "0"))
            elif name == "MarginRight":
                margins["right"] = str(param.get("Value", "0"))
            elif name == "MarginTop":
                margins["top"] = str(param.get("Value", "0"))
            elif name == "MarginBottom":
                margins["bottom"] = str(param.get("Value", "2cm")) # DEFAULT AL MIO MARGINE ALLA FINE
            elif name == "PageSize":
                page_size = param.get("Value", "A4")

        # Se i valori presi da n8n sono testuali vuoti o stringa "0", imposto i margini che volevi
        if margins["top"] == "0" or not margins["top"]: margins["top"] = "1cm"
        if margins["right"] == "0" or not margins["right"]: margins["right"] = "1cm"
        if margins["left"] == "0" or not margins["left"]: margins["left"] = "1cm"
        if margins["bottom"] == "0" or not margins["bottom"]: margins["bottom"] = "2cm"

        # Funzione helper per aggiungere "cm" ai margini se l'utente manda solo numeri > 0
        def format_margin(val):
            val = val.strip()
            if val.isdigit() and val != "0":
                return val + "cm"
            return val
            
        margins = {k: format_margin(v) for k, v in margins.items()}

        if not html_base64:
            await Actor.fail(status_message="Errore: Nessun contenuto HTML (Data) fornito in input nel parametro 'File'.")
            return

        # Decodifica il Base64 per ottenere la stringa HTML
        try:
             # Stampa i primi 50 caratteri del base64 ricevuto per il debug
            Actor.log.info(f"Ricevuto HTML Base64 (primi 50 char): {html_base64[:50]}")
            
            # Pulisce la stringa da spazi bianchi o newline indesiderati
            html_base64 = html_base64.strip()
            
            import urllib.parse
            # Decodifica eventuali caratteri URL-encoded passati da n8n
            html_base64 = urllib.parse.unquote(html_base64)
            
            # Rimuove l'eventuale prefisso "data:text/html;base64," se presente
            if "," in html_base64:
                html_base64 = html_base64.split(",", 1)[1]
                
            # Aggiunge il padding (=) corretto se n8n ha inviato una stringa tagliata
            missing_padding = len(html_base64) % 4
            if missing_padding:
                html_base64 += '=' * (4 - missing_padding)

            html_content = base64.b64decode(html_base64).decode("utf-8")
        except Exception as e:
            await Actor.fail(status_message=f"Errore nella decodifica base64: {e}. Stringa in ingresso: {html_base64[:100]}...")
            return

        Actor.log.info("Codice HTML decodificato con successo. Avvio di Playwright per la generazione del PDF...")
        
        async with async_playwright() as p:
            # Chromium headless per l'ambiente Linux dockerizzato di Apify
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()
            
            # Carica il contenuto HTML
            await page.set_content(html_content, wait_until="networkidle")
            
            # Generazione del PDF in memoria come array di byte
            Actor.log.info(f"Stampando in formato {page_size} con margini {margins}...")
            pdf_bytes = await page.pdf(
                format=page_size,
                print_background=True,
                margin=margins
            )
            
            await browser.close()
            
        Actor.log.info("PDF generato con successo! Salvataggio nel Key-Value store...")
        
        # Salva il risultato nel Key-Value store di Apify
        await Actor.set_value("OUTPUT", pdf_bytes, content_type="application/pdf")
        
        # Recupera l'URL pubblico del PDF generato per inviarlo a n8n
        store = await Actor.open_key_value_store()
        pdf_public_url = await store.get_public_url("OUTPUT")
        
        # Pusha i risultati nel dataset (che sarà la risposta JSON che n8n riceverà direttamente)
        await Actor.push_data([
            {
                "status": "success",
                "pdf_url": pdf_public_url,
                "message": "Conversione HTML -> PDF completata!"
            }
        ])
        
        Actor.log.info(f"Finito. Il link al PDF è disponibile su: {pdf_public_url}")

if __name__ == "__main__":
    asyncio.run(main())
