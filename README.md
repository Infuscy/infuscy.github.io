# infuscy.github.io

Frontend pentru rapoarte statice de investigatii de date. Gazduieste rapoarte interactive despre rezultatele Bacalaureatului (si alte seturi de date viitoare). Fiecare raport ruleaza complet in browser — zero backend.

## Structura

- **`_posts/`** — un post Jekyll per raport. Postul descrie cardul din grid si modal-ul cu link catre raport.
- **subdirectoarele de rapoarte** (`bac2025/`, `bac2026/`, `bac2526/`) — build-uri statice Vite (`web/dist/`) copiate din repo-urile fiecarui raport. Servite de GitHub Pages la `infuscy.github.io/<dir>/`.
- **`img/portfolio/`** — thumbnaily pentru cardurile din grid.
- Tema actuala: Jekyll + Start Bootstrap "Freelancer" (GitHub Pages build automat la push).

## Adaugarea unui raport nou

1. Construieste raportul din repo-ul sau: `npm run build` (produce `web/dist/`).
2. Copiaza `web/dist/` in acest repo, intr-un subdirector nou, ex: `bac2027/`.
3. Creeaza un post in `_posts/YYYY-MM-DD-slug.markdown` cu un `modal-id` unic (incremental) si un link in `description` catre `/<dir>/`. Vezi posturile existente pentru format.
4. Adauga un thumbnail in `img/portfolio/` (referentiat in postul nou, campul `img`).
5. Push — GitHub Pages publica automat atat indexul, catit noul raport.

## Rulare locala

Necesita Jekyll (Ruby). Din root-ul repo-ului:

```bash
bundle exec jekyll serve
```

Apoi deschide `http://localhost:4000`. Grid-ul din `index.html` iti arata toate posturile; click pe un card deschide modal-ul cu link catre subdirectorul raportului.
