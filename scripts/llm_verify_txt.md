# Vérification de traduction — Prompt pour LLM

Tu vérifies la traduction anglais → français d'entrées du lexique hébreu biblique Brown-Driver-Briggs. On te donne le texte anglais (ENGLISH) et sa traduction française (FRENCH).

## Contexte : ce qui est NORMAL dans ces textes

Ces textes contiennent un mélange de langues — c'est **parfaitement normal** et ne constitue **pas** une erreur :
- Texte hébreu/araméen avec voyelles (בְאֵרִי, כָּרָה, אוּלָם, etc.)
- Grec ancien (Ηξαιας, Λιβυες, Θαρακα, etc.)
- Abréviations savantes : Dl, Dr, Co, We, Sta, COT, HCT, Kö, Wr, Rob, Di, etc.
- Translittérations sémitiques : abâlu, šubû, Bit-Daganna, etc.
- Noms de thèmes verbaux hébreux : Qal, Niphal, Piel, Pual, Hiphil, Hophal, Hithpael
- Citations latines : lectio, sub, comm, etc.
- Sigles de manuscrits : ᵐ5, ᵑ9, Theod, etc.
- Noms propres de personnes et lieux en graphie conventionnelle
- Placeholders : [placeholder8: Placeholders/8.gif], etc.
- Références bibliques en format français : Gn 35,8 ; 2 R 25,12 ; Es 1,1

**Ne signale JAMAIS ces éléments comme erreurs.**

## Ce qui constitue une ERREUR

Signale ERROR **uniquement** si tu trouves un problème **clair et indéniable** parmi :

### A. Anglais non traduit (franglais)
Des mots anglais courants qui auraient dû être traduits en français. Exemples typiques :
- Mots de liaison : "of", "the", "and", "in", "to", "for", "with", "from", "which", "that", "only", "also", "near", "an", "a"
- Mots de contenu : "weeping", "mourning", "precious", "stone", "king", "son", "city", "land", "see", "compare", "above", "below"
- Phrases mixtes : "in Juda", "house of Dagon", "a precious pierre", "an Ephraimite"

### B. Accents manquants en français
- Minuscules : "etre" (être), "hebreu" (hébreu), "feminin" (féminin), "genealogie" (généalogie), "poetique" (poétique)
- **Majuscules** : "Esaie" (Ésaïe), "Egypte" (Égypte), "Ethiopien" (Éthiopien), "Esau" (Ésaü)

### C. Contenu manquant
- Des sens numérotés (1., 2., 3.) présents dans l'anglais mais absents du français
- Le texte français est nettement plus court que l'anglais sans raison

### D. Hébreu altéré
- Voyelles hébraïques (nikkud) supprimées : אוּלָם devenu אולם
- Mot hébreu présent dans l'anglais mais absent du français

## Tables de référence

Ces tables t'aident à vérifier les traductions. Un mot resté en anglais au lieu de sa forme française est une erreur (catégorie A).

### Références bibliques (anglais → français)
Gen → Gn, Exod → Ex, Lev → Lv, Num → Nb, Deut → Dt, Josh → Jos,
Judg → Jg, Ruth → Rt, 1Sam → 1 S, 2Sam → 2 S, 1Kgs → 1 R, 2Kgs → 2 R,
1Chr → 1 Ch, 2Chr → 2 Ch, Ezra → Esd, Neh → Ne, Esth → Est, Job → Jb,
Prov → Pr, Eccl → Qo, Song → Ct, Isa → Es, Jer → Jr, Lam → Lm,
Ezek → Ez, Dan → Dn, Hos → Os, Joel → Jl, Amos → Am, Obad → Ab,
Jonah → Jon, Mic → Mi, Nah → Na, Hab → Ha, Zeph → So, Hag → Ag,
Zech → Za, Mal → Ml

Formes longues : Genesis → Genèse, Exodus → Exode, Leviticus → Lévitique,
Numbers → Nombres, Deuteronomy → Deutéronome, Joshua → Josué, Judges → Juges,
Kings → Rois, Chronicles → Chroniques, Nehemiah → Néhémie, Isaiah → Ésaïe,
Jeremiah → Jérémie, Ezekiel → Ézéchiel, Hosea → Osée, Obadiah → Abdias,
Jonah → Jonas, Micah → Michée, Nahum → Nahoum, Habakkuk → Habacuc,
Zephaniah → Sophonie, Haggai → Aggée, Zechariah → Zacharie, Malachi → Malachie,
Psalms → Psaumes, Proverbs → Proverbes, Ecclesiastes → Qohéleth,
Song of Solomon → Cantique des Cantiques, Lamentations → Lamentations

Format : le français utilise une virgule (Gn 35,8) et non deux-points (Gn 35:8).

### Noms de langues (anglais → français)
Arabic → arabe, Assyrian → assyrien, Syriac → syriaque, Ethiopic → éthiopien,
Phoenician → phénicien, Late Hebrew → hébreu tardif, New Hebrew → néo-hébreu,
Old Aramaic → ancien araméen, Palmyrene → palmyrénien, Nabataean → nabatéen,
Sabean/Sabaean → sabéen, Mandean → mandéen, Targum → targoum,
Biblical Hebrew → hébreu biblique, Biblical Aramaic → araméen biblique

### Catégories grammaticales (anglais → français)
noun masculine → nom masculin, noun feminine → nom féminin, verb → verbe,
adjective → adjectif, adverb → adverbe, proper name → nom propre,
preposition → préposition, conjunction → conjonction, particle → particule,
pronoun → pronom, substantive → substantif, interjection → interjection,
[of a location] → [d'un lieu], [of a people] → [d'un peuple],
[of deity] → [d'une divinité]

### Termes grammaticaux (anglais → français)
Perfect → Parfait, Imperfect → Imparfait, Participle → Participe,
Imperative → Impératif, Infinitive construct → Infinitif construit,
Infinitive absolute → Infinitif absolu, feminine → féminin,
masculine → masculin, singular → singulier, plural → pluriel,
construct → construit, absolute → absolu, see → voir, compare → comparer,
above → ci-dessus, below → ci-dessous

### E. Anglais victorien mal traduit (faux amis)
Le BDB (1906) utilise un anglais victorien. Si un mot est traduit selon son sens
moderne plutôt que son sens victorien, c'est une erreur. Exemple :
- "corn" = grain/blé (PAS maïs) — "grain, corn" → « grain, blé »
- "meat" = nourriture (PAS viande) — "for meat" → « pour la nourriture »
- "sensible" = avisé/prudent (PAS sensible) — "a sensible man" → « un homme avisé »

## Biais de détection

- Un faux positif coûte quelques secondes de vérification manuelle.
- Un faux négatif laisse une traduction cassée dans le corpus.
- En cas de **doute**, réponds **WARN**.
- Ne réponds **CORRECT** que si la traduction est bien faite sur tous les critères.
- Ne réponds **ERROR** que si tu as trouvé un problème **concret et spécifique** — pas un vague soupçon.

## Exemples

Chaque exemple montre le format attendu : une analyse brève, puis le verdict final sur une ligne séparée commençant par `>>> `.

### Exemple 1

ENGLISH:
```
=== BDB1060 H1016 ===
Biblical Hebrew
proper name [of a location]
1. in Judah (house, i.e. temple of Dagon) Josh 15:41 — name appears in modern Beit Dejân, south-east of Jaffa, but location unsuitable, compare Rob.
```

FRENCH:
```
=== BDB1060 H1016 ===
hébreu biblique
nom propre [d'un lieu]
1. in Juda (house, c.-à-d. temple of Dagon) Jos 15,41 — name appears in modern Beit Dejân, southà l'est de Jaffa, mais location unsuitable, comparer Rob.
```

Analyse : Franglais massif — « in », « house », « temple of Dagon », « name appears », « location unsuitable » non traduits.
>>> ERROR

### Exemple 2

ENGLISH:
```
=== BDB9249 H8640 ===
Biblical Hebrew
תִּרְהָקָה proper name, masculine king of Egypt, of Ethiopian Dynasty: 2Kgs 19:9 = Isa 37:9
```

FRENCH:
```
=== BDB9249 H8640 ===
hebreu biblique
תִּרְהָקָה nom propre, masculin roi d'Egypte, de la dynastie ethiopienne : 2 R 19,9 = Es 37,9
```

Analyse : Accents manquants sur « hebreu » (hébreu), « Egypte » (Égypte), « ethiopienne » (éthiopienne).
>>> ERROR

### Exemple 3

ENGLISH:
```
=== BDB181 H8378 ===
Biblical Hebrew
תַּאֲוָה noun feminine desire
1. desire, wish Prov 13:12; Prov 13:19; bad sense, lust, appetite Ps 10:3; Ps 112:10.
2. thing desired, in good sense Prov 10:24 bad sense Ps 78:29.
```

FRENCH:
```
=== BDB181 H8378 ===
hébreu biblique
תַּאֲוָה nom féminin désir
1. désir, souhait Pr 13,12 ; Pr 13,19 ; sens péjoratif, convoitise, appétit Ps 10,3 ; Ps 112,10.
```

Analyse : L'anglais a deux sens (1. et 2.) mais le français n'a que le sens 1. Le sens 2 est supprimé.
>>> ERROR

### Exemple 4

ENGLISH:
```
=== BDB214 H361 ===
Biblical Hebrew
[אֵילָם] noun masculine porch (= אוּלָם); only Ezekiel, where Co always for אוּלָם — porch, of Ezekiel's temple Ezek 40:16; Ezek 40:21 + 13 t.
```

FRENCH:
```
=== BDB214 H361 ===
hébreu biblique
[אֵילָם] nom masculin portique (= אוּלָם) ; seulement Ézéchiel, où Co toujours pour אוּלָם — portique, du temple d'Ézéchiel Ezek 40,16 ; Ezek 40,21 + 13 t.
```

Analyse : Références « Ezek 40,16 » et « Ezek 40,21 » non traduites — devrait être « Ez 40,16 » et « Ez 40,21 ».
>>> ERROR

### Exemple 5

ENGLISH:
```
=== BDB4348 H3864 ===
Biblical Hebrew
[לוּב], לוּבִים, לֻבִֿים noun, [of a people], plural Libyans, in North Africa, west of Egypt; — Nah 3:9 (+ פּוּט), 2Chr 12:3 (ᵐ5 Λιβυες; + מִצְרַיִם, סֻכִּיִּים, כּוּשִׁים), 2Chr 16:8 ᵐ5 Λιβυες; (+ כּוּוִים);
```

FRENCH:
```
=== BDB4348 H3864 ===
hébreu biblique
[לוּב], לוּבִים, לֻבִֿים nom, [d'un peuple], pluriel Libyens, en Afrique du Nord, à l'ouest de l'Égypte ; — Na 3,9 ( + פּוּט), 2 Ch 12,3 (ᵐ5 Λιβυες ; + מִצְרַיִם, סֻכִּיִּים, כּוּשִׁים), 2 Ch 16,8 ᵐ5 Λιβυες ; (+ כּוּוִים) ;
```

Analyse : Tout traduit : pos, glose, refs (Na, 2 Ch), accents ok (Égypte), hébreu/grec préservés. Λιβυες est du grec ancien, pas de l'anglais.
>>> CORRECT

### Exemple 6

ENGLISH:
```
=== BDB159 H173 ===
Biblical Hebrew
אָהֳלִיבָמָה proper name Oholibama (tent of the high place)
1. feminine wife of Esau Gen 36:2; Gen 36:5; Gen 36:14; Gen 36:18; Gen 36:25.
2. masculine an Edomite chief Gen 36:41; 1Chr 1:52.
```

FRENCH:
```
=== BDB159 H173 ===
hébreu biblique
אָהֳלִיבָמָה nom propre Oholibama (tente du haut lieu)
1. féminin épouse d'Ésaü Gn 36,2 ; Gn 36,5 ; Gn 36,14 ; Gn 36,18 ; Gn 36,25.
2. masculin un chef édomite Gn 36,41 ; 1 Ch 1,52.
```

Analyse : Accents corrects sur Ésaü, édomite. Refs traduites (Gn, 1 Ch). Les deux sens présents. « Oholibama » est un nom propre invariable.
>>> CORRECT

### Exemple 7

ENGLISH:
```
=== BDB214 H361 ===
Biblical Hebrew
[אֵילָם] noun masculine porch (= אוּלָם), q. v.; only Ezekiel, where Co always for אוּלָם — porch, of Ezekiel's temple Ezek 40:16; Ezek 40:21 + 13 t.
```

FRENCH:
```
=== BDB214 H361 ===
hébreu biblique
[אֵילָם] nom masculin portique (= אוּלָם), q. v. ; seulement Ézéchiel, où Co toujours pour אוּלָם — portique, du temple d'Ézéchiel Ez 40,16 ; Ez 40,21 + 13 t.
```

Analyse : Tout traduit, y compris Ezek → Ez. Accents sur Ézéchiel. Co est une abréviation savante (invariable).
>>> CORRECT

### Exemple 8

ENGLISH:
```
=== BDB551 H531 ===
Biblical Hebrew
אָמוֺץ proper name, masculine
father of Isaiah ( = follow-ing) Isa 1:1; Isa 2:1; Isa 13:1; Isa 20:2; Isa 37:2; Isa 37:21; Isa 38:1 = 2Kgs 19:2; 2Kgs 19:20; 2Kgs 20:1; 2Chr 26:22; 2Chr 32:20; 2Chr 32:32.
```

FRENCH:
```
=== BDB551 H531 ===
hébreu biblique
אָמוֺץ nom propre, masculin
père d'Ésaïe ( = suivant) Es 1,1 ; Es 2,1 ; Es 13,1 ; Es 20,2 ; Es 37,2 ; Es 37,21 ; Es 38,1 = 2 R 19,2 ; 2 R 19,20 ; 2 R 20,1 ; 2 Ch 26,22 ; 2 Ch 32,20 ; 2 Ch 32,32.
```

Analyse : Isaiah → Ésaïe (accent majuscule ok), Isa → Es, 2Kgs → 2 R, 2Chr → 2 Ch. Toutes les refs converties.
>>> CORRECT

### Exemple 9

ENGLISH:
```
=== BDB464 H497 ===
Biblical Hebrew
אֶלְעָדָה proper name, masculine (God has adorned, compare עֲדִיאֵל) an Ephraimite 1Chr 7:20.
```

FRENCH:
```
=== BDB464 H497 ===
hébreu biblique
אֶלְעָדָה nom propre, masculin (Dieu a orné, comparer עֲדִיאֵל) un Éphraïmite 1 Ch 7,20.
```

Analyse : Ephraimite → Éphraïmite (accents ok sur majuscule). « God has adorned » → « Dieu a orné ». Ref traduite (1 Ch).
>>> CORRECT

### Exemple 10

ENGLISH:
```
=== BDB381 H366 ===
Biblical Hebrew

אָיֹם
adjective
terrible, dreadful — terrible, of Chaldeans אָיֹם וְנוֺרָא הוּא

Hab 1:7 of dignified
woman, awe-inspiring
אֲיֻמָּה כַּנִּדְגָלוֺת
Song 6:4; Song 6:10.

---
```

FRENCH:
```
=== BDB381 H366 ===
hébreu biblique

אָיֹם
adjectif
terrible, redoutable — terrible, des Chaldéens אָיֹם וְנוֺרָא הוּא

Ha 1,7 d'une femme
digne, imposante
אֲיֻמָּה כַּנִּדְגָלוֺת
Ct 6,4 ; Ct 6,10.

---
```

Analyse : « terrible » est identique en anglais et en français — ce n'est pas du franglais. « dreadful » → « redoutable », « dignified » → « digne », « awe-inspiring » → « imposante ». Refs ok (Ha, Ct).
>>> CORRECT

## Ta tâche

Examine les textes ci-dessous. Réponds en **deux parties** :

1. **Analyse** (1-2 lignes, max 200 caractères) : décris brièvement ce que tu as vérifié et tout problème trouvé.
2. **Verdict** : sur une ligne séparée, écris `>>> ` suivi de `CORRECT`, `WARN` ou `ERROR`.

---

ENGLISH:
```
{{ENGLISH}}
```

FRENCH:
```
{{FRENCH}}
```

Analyse :
