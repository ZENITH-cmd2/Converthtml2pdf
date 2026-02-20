# Usa l'immagine ufficiale Apify configurata per Python e Playwright
FROM apify/actor-python-playwright:3.12

# Copia la lista delle dipendenze e installale
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium

# Copia tutto il resto del codice sorgente
COPY . ./

# Indica ad Apify quale file eseguire
CMD ["python3", "converter.py"]
