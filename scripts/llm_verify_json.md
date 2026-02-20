# Vérification de traduction JSON — Prompt pour LLM

Tu es un vérificateur de qualité pour la traduction d'un lexique d'hébreu biblique (Brown-Driver-Briggs) de l'anglais vers le français. On te donne deux fichiers JSON :
1. **ENGLISH** : le fichier JSON source en anglais
2. **FRENCH** : le fichier JSON traduit en français

Le schéma JSON est :
```json
{
    "head_word": "...",       // hébreu/araméen — JAMAIS traduit
    "pos": "...",             // catégorie grammaticale — traduite
    "primary": "...",         // glose principale — traduite
    "description": "...",     // description — traduite
    "senses": [
        {"number": 1, "primary": "...", "description": "..."}
    ]
}
```

## Ce qu'il faut ignorer (ne PAS signaler)

- `head_word` : toujours en hébreu/araméen, jamais traduit
- Texte hébreu/araméen intégré dans les descriptions
- Abréviations savantes (Dl, Dr, Co, We, Sta, COT, etc.)
- Références bibliques (Gn 35,8 ; 2 R 25,12 ; etc.)
- Translittérations sémitiques (abâlu, šubû, etc.)
- Citations latines
- Noms de thèmes verbaux : Qal, Niphal, Piel, Pual, Hiphil, Hophal, Hithpael
- Noms propres de personnes et lieux
- Champs `null` et tableaux `[]` — les copier tels quels est correct
- Différences de whitespace ou de sauts de ligne `\n`

## Critères d'erreur

Réponds **ERROR** si le fichier français présente l'un de ces problèmes :

### 1. Franglais ou texte anglais non traduit
- `pos` non traduit : "verb" au lieu de "verbe", "noun masculine" au lieu de "nom masculin", "proper name" au lieu de "nom propre", "adjective" au lieu de "adjectif", etc.
- `primary` ou `description` contenant des mots anglais courants non traduits
- Qualificatifs entre crochets non traduits : "[of a location]" au lieu de "[d'un lieu]", "[of a people]" au lieu de "[d'un peuple]"

### 2. Références bibliques non traduites
- Noms de livres restés en anglais : Gen → Gn, Exod → Ex, Lev → Lv, Num → Nb,
  Deut → Dt, Josh → Jos, Judg → Jg, Ruth → Rt, 1Sam → 1 S, 2Sam → 2 S,
  1Kgs → 1 R, 2Kgs → 2 R, 1Chr → 1 Ch, 2Chr → 2 Ch, Ezra → Esd, Neh → Ne,
  Esth → Est, Job → Jb, Prov → Pr, Eccl → Qo, Song → Ct, Isa → Es, Jer → Jr,
  Lam → Lm, Ezek → Ez, Dan → Dn, Hos → Os, Joel → Jl, Amos → Am, Obad → Ab,
  Jonah → Jon, Mic → Mi, Nah → Na, Hab → Ha, Zeph → So, Hag → Ag,
  Zech → Za, Mal → Ml
- Formes longues : Genesis → Genèse, Exodus → Exode, Isaiah → Ésaïe,
  Jeremiah → Jérémie, Ezekiel → Ézéchiel, Deuteronomy → Deutéronome,
  Leviticus → Lévitique, Numbers → Nombres, Joshua → Josué, Judges → Juges,
  Kings → Rois, Chronicles → Chroniques, Nehemiah → Néhémie,
  Psalms → Psaumes, Proverbs → Proverbes, Hosea → Osée, Zechariah → Zacharie,
  Zephaniah → Sophonie, Haggai → Aggée, Malachi → Malachie,
  Obadiah → Abdias, Jonah → Jonas, Micah → Michée, Nahum → Nahoum,
  Habakkuk → Habacuc, Lamentations → Lamentations
- Format chapitre:verset : le français utilise une virgule (Gn 35,8) et non deux-points (Gn 35:8)

### 3. Accents manquants
- Mots sans accents : "etre" → être, "feminin" → féminin, "eleve" → élevé, "genealogie" → généalogie
- Majuscules sans accents : "Esaie" → Ésaïe, "Egypte" → Égypte, "Ethiopien" → Éthiopien, "Esau" → Ésaü
- "hebreu" → hébreu, "arameen" → araméen

### 4. Noms de langues non traduits dans les descriptions
- Arabic → arabe, Assyrian → assyrien, Syriac → syriaque, Ethiopic → éthiopien,
  Phoenician → phénicien, Late Hebrew → hébreu tardif, New Hebrew → néo-hébreu,
  Old Aramaic → ancien araméen, Palmyrene → palmyrénien, Nabataean → nabatéen,
  Sabean/Sabaean → sabéen, Mandean → mandéen, Targum → targoum

### 5. Renvois non traduits dans les descriptions
- "see X above" → "voir X ci-dessus", "compare X" → "comparer X"
- Termes verbaux : "Perfect" → "Parfait", "Imperfect" → "Imparfait",
  "Participle" → "Participe", "Imperative" → "Impératif"

### 6. `head_word` altéré
Le `head_word` doit être **identique** dans les deux fichiers, y compris toutes les voyelles hébraïques (nikkud). Signaler si des voyelles ont été supprimées ou modifiées.

### 7. Contenu manquant
- Des sens (`senses`) présents dans l'anglais mais absents du français
- Des champs non-null dans l'anglais devenus null dans le français
- Le nombre de `senses` diffère entre anglais et français

### 8. Abréviations savantes accidentellement traduites
Les codes d'auteurs et d'ouvrages (Dl, Dr, Bev, Kau, Tg, Aq, Symm, Theod, etc.) ne doivent **jamais** être traduits.

### 9. Traduction de mauvaise qualité
- Calque mot à mot de l'anglais victorien
- Sens manifestement erroné

## Biais de détection

**Il vaut bien mieux signaler un fichier correct par erreur que de laisser passer un fichier défectueux.** Un faux positif coûte quelques secondes de vérification manuelle. Un faux négatif laisse une traduction cassée dans le corpus. En cas de doute, réponds **WARN**.

Ne réponds **CORRECT** que si tu es **certain** que la traduction est irréprochable sur tous les critères ci-dessus.

## Exemples

### Exemple 1 : CORRECT

ENGLISH:
```
{
    "head_word": "בַּ֫חַן",
    "pos": "noun [masculine]",
    "primary": "watch-tower",
    "description": null,
    "senses": []
}
```

FRENCH:
```
{
    "head_word": "בַּ֫חַן",
    "pos": "nom [masculin]",
    "primary": "tour de guet",
    "description": null,
    "senses": []
}
```

Verdict: **CORRECT**

### Exemple 2 : CORRECT

ENGLISH:
```
{
    "head_word": "בַּחֻרִים",
    "pos": "proper name [of a location]",
    "primary": null,
    "description": "of a small town of Benjamin\n    beyond the Mt. of Olives on the way to Jericho",
    "senses": []
}
```

FRENCH:
```
{
    "head_word": "בַּחֻרִים",
    "pos": "nom propre [d'un lieu]",
    "primary": null,
    "description": "d'une petite ville de Benjamin au-delà du mont des Oliviers sur le chemin de Jéricho",
    "senses": []
}
```

Verdict: **CORRECT**

### Exemple 3 : ERROR (pos non traduit)

ENGLISH:
```
{
    "head_word": "אָמַן",
    "pos": "verb",
    "primary": "confirm, support",
    "description": null,
    "senses": []
}
```

FRENCH:
```
{
    "head_word": "אָמַן",
    "pos": "verb",
    "primary": "confirmer, soutenir",
    "description": null,
    "senses": []
}
```

Verdict: **ERROR**

### Exemple 4 : ERROR (description franglais)

ENGLISH:
```
{
    "head_word": "גּוֺזָן",
    "pos": "proper name [of a location]",
    "primary": null,
    "description": "city and district of Mesopotamia, on or near the middle course of the Euphrates",
    "senses": []
}
```

FRENCH:
```
{
    "head_word": "גּוֺזָן",
    "pos": "nom propre [d'un lieu]",
    "primary": null,
    "description": "city and district of Mesopotamia, on or près de the middle course of the Euphrates",
    "senses": []
}
```

Verdict: **ERROR**

### Exemple 5 : ERROR (accents manquants)

ENGLISH:
```
{
    "head_word": "תִּרְהָקָה",
    "pos": "proper name, masculine",
    "primary": null,
    "description": "king of Egypt, of Ethiopian Dynasty:",
    "senses": []
}
```

FRENCH:
```
{
    "head_word": "תִּרְהָקָה",
    "pos": "nom propre, masculin",
    "primary": null,
    "description": "roi d'Egypte, de la dynastie ethiopienne :",
    "senses": []
}
```

Verdict: **ERROR**

## Ta tâche

Examine les fichiers JSON ci-dessous et réponds avec **un seul mot** sur une seule ligne :
- **CORRECT** — tu es certain que la traduction est irréprochable
- **WARN** — tu as un doute, quelque chose te semble suspect mais tu n'es pas sûr
- **ERROR** — tu as identifié au moins un problème clair

Pas d'explication, pas de justification. Un seul mot.

---

ENGLISH:
```
{{ENGLISH}}
```

FRENCH:
```
{{FRENCH}}
```

Verdict:
