# Usa l'immagine ufficiale Apify configurata per Python e Playwright
FROM apify/actor-python-playwright:default

# Copia la lista delle dipendenze e installale
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice sorgente
COPY . ./

# Indica ad Apify quale file eseguire
CMD ["python3", "-m", "apify", "run", "-p", "converter.py"]
