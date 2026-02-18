# Brown-Driver-Briggs Enhanced -- Projet de lexique français

## Présentation du projet

Le Brown-Driver-Briggs Hebrew and English Lexicon (BDB) est le dictionnaire de
référence pour l'hébreu biblique et l'araméen. Publié initialement en 1906, ses
définitions anglaises emploient une prose victorienne archaïque, parfois guindée.

Ce projet maintient une extraction JSON structurée de chaque entrée BDB
(`json_output/`, ~10 022 fichiers) ainsi que les entrées HTML originales
(`Entries/`). L'objectif de la **conversion en lexique français** est de
produire un ensemble parallèle de fichiers JSON (`json_output_fr/`) et HTML
(`Entries_fr/`) où tout le contenu en anglais est rendu en français moderne et
clair, tout en préservant intégralement chaque mot-vedette hébreu ou araméen,
chaque lemme et chaque notation morphologique.

## Arborescence

```
Brown-Driver-Briggs-Enhanced/
    Entries/            # Entrées HTML originales du BDB (lecture seule)
    Entries_txt/        # Texte brut extrait des entrées HTML (généré par script)
    Entries_txt_fr/     # Texte brut traduit en français (par LLM)
    Entries_fr/         # Entrées HTML en français (réassemblé par LLM)
    json_output/        # JSON anglais, un fichier par entrée BDB (source)
    json_output_fr/     # JSON français, un fichier par entrée BDB (cible)
    Placeholders/       # ~6 200 images GIF de scripts de langues apparentées
    scripts/            # Outils du pipeline de traduction
        extract_txt.py  # Entries/ -> Entries_txt/ (extraction déterministe)
        validate_html.py # Vérification de Entries_fr/ contre originaux
        untranslated.py # Liste les fichiers non encore traduits
    bdbToStrongsMapping.csv
    placeholders.csv
    CLAUDE.md           # Instructions spécifiques au projet
    AGENTS.md           # Ce fichier -- instructions pour les agents LLM
```

## Accents et UTF-8

**Toute sortie en français DOIT utiliser les accents et diacritiques corrects, y compris sur les lettres majuscules.**
Il s'agit d'un ouvrage de référence savant ; le français sans accents est
inacceptable. Exemples :

- « usé » et non « use », « blé » et non « ble », « être » et non « etre »
- « féminin » et non « feminin », « généalogie » et non « genealogie »
- « Néhémie » et non « Nehemie », « Deutéronome » et non « Deuteronome »
- « c.-à-d. » et non « c.-a-d. », « là » et non « la » (quand c'est l'adverbe)
- « hébreu » et non « hebreu », « araméen » et non « arameen »
- « phénicien » et non « phenicien », « éthiopien » et non « ethiopien »
- « fraîcheur » et non « fraicheur », « première » et non « premiere »
- « Ésaïe » et non « Esaie », « Ézéchiel » et non « Ezechiel »
- « À partir de » et non « A partir de », « État » et non « Etat »

Tous les fichiers de sortie (JSON et HTML) sont en UTF-8. Chaque caractère
accentué (é, è, ê, ë, à, â, ù, û, ô, î, ï, ç, etc.) doit apparaître comme
le codepoint Unicode réel, jamais comme une entité HTML et jamais réduit à
l'ASCII.

## Schéma des entrées JSON

Chaque fichier dans `json_output/` (et son équivalent français) a cette forme :

```json
{
    "head_word": "אֵב",              // hébreu/araméen -- NE JAMAIS traduire
    "pos": "noun [masculine]",       // catégorie grammaticale -- traduire
    "primary": "freshness, fresh green",  // glose -- traduire
    "description": "one who tries metals", // note -- traduire
    "senses": [
        {
            "number": 1,
            "primary": "...",        // glose du sens -- traduire
            "description": "..."     // note du sens -- traduire
        }
    ]
}
```

### Règles de traduction

1. **`head_word`** : Toujours en écriture hébraïque ou araméenne. Copier tel
   quel ; ne jamais modifier.
2. **`pos`** (catégorie grammaticale) : Traduire l'étiquette grammaticale en
   français. Correspondances courantes :
   - "noun masculine" -> "nom masculin"
   - "noun feminine" -> "nom féminin"
   - "noun [masculine]" -> "nom [masculin]"
   - "verb" -> "verbe"
   - "adjective" -> "adjectif"
   - "adverb" -> "adverbe"
   - "preposition" -> "préposition"
   - "conjunction" -> "conjonction"
   - "particle" -> "particule"
   - "pronoun" -> "pronom"
   - "proper name" -> "nom propre"
   - "proper name, masculine" -> "nom propre, masculin"
   - "proper name [of a location]" -> "nom propre [d'un lieu]"
   - "proper name [of a people]" -> "nom propre [d'un peuple]"
   - "proper name [of deity]" -> "nom propre [d'une divinité]"
   - "interjection" -> "interjection"
   - "substantive" -> "substantif"
   - "collective noun feminine" -> "nom collectif féminin"
   - "plural" -> "pluriel"
   - "verbal adjective" -> "adjectif verbal"
   - "verbal noun" -> "nom verbal"
   - Les qualificatifs entre crochets : "[of a people]" -> "[d'un peuple]", etc.
   - En cas de doute, préférer un équivalent grammatical français littéral.
3. **`primary`** : La glose anglaise principale. Traduire en français moderne
   et naturel.
   - "freshness, fresh green" -> "fraîcheur, vert frais"
   - "mourn" -> "pleurer, porter le deuil"
   - "choose" -> "choisir"
   - "gift" -> "don, cadeau"
   - "worn out" -> "usé"
   - "be crushed" -> "être écrasé"
   - "grain, corn" -> "grain, blé"
   - Les noms propres (lieux, personnes) restent inchangés : "Ellasar"
     demeure "Ellasar".
4. **`description`** : Texte explicatif plus long. Traduire en français moderne.
   Préserver telles quelles les chaînes en hébreu/araméen. Préserver les
   abréviations savantes et les références bibliques.
5. **`senses[].primary`** et **`senses[].description`** : Mêmes règles que pour
   `primary` et `description` de niveau supérieur.
6. **Valeurs `null`** : Copier comme `null`. Ne rien inventer.
7. **Tableaux vides** : Copier comme `[]`.
8. **Formatage** : Respecter l'indentation à 4 espaces du JSON source.
   Pas d'espace en fin de ligne.

## Exemples de traduction

Ces exemples montrent les traductions anglais-français correctes. Chaque
exemple utilise les accents appropriés. Les balises sont retirées pour la
lisibilité ; dans les fichiers réels, la structure de balisage doit être
préservée.

### Exemples JSON (json_output/ -> json_output_fr/)

**BDB50** -- אָבַל "mourn" (verb)
```
English:  pos = "verb"           primary = "mourn"
French:   pos = "verbe"          primary = "pleurer, porter le deuil"
```

**BDB100** -- אִגֶּ֫רֶת "letter" (noun feminine)
```
English:  pos = "noun feminine"  primary = "letter, letter-missive"
French:   pos = "nom féminin"    primary = "lettre, lettre missive"
```

**BDB500** -- אֶלָּסָר "Ellasar" (proper name of a location)
```
English:  pos = "proper name [of a location]"  primary = "Ellasar"
French:   pos = "nom propre [d'un lieu]"        primary = "Ellasar"
```

**BDB1123** -- בָּלֶה "worn out" (adjective)
```
English:  pos = "adjective"      primary = "worn out"
French:   pos = "adjectif"       primary = "usé"
```

**BDB1352** -- בַּר "grain" (noun masculine)
```
English:  pos = "noun masculine" primary = "grain, corn"
French:   pos = "nom masculin"   primary = "grain, blé"
```

**BDB1765** -- גָּרַס "be crushed" (verb)
```
English:  pos = "verb"   primary = "be crushed"   description = "i.e. perisheth"
French:   pos = "verbe"  primary = "être écrasé"   description = "c.-à-d. périt"
```

**BDB200** -- אוּלָם (proper name, masculine)
```
English:  pos = "proper name, masculine"  description = "only genealogy"
French:   pos = "nom propre, masculin"    description = "seulement généalogie"
```

**BDB5** -- אֲבַגְתָא (proper name, masculine -- eunuch)
```
English:  pos = "proper name, masculine"  description = "eunuch of Ahasuerus"
French:   pos = "nom propre, masculin"    description = "eunuque d'Assuérus"
```

**BDB3000** -- חָפַף "enclose, surround" (verb)
```
English:  pos = "verb"   primary = "enclose, surround, cover"
French:   pos = "verbe"  primary = "enfermer, entourer, couvrir"
```

**BDB1** -- א (entrée de lettre)
```
English:  description = "Aleph, first letter"
French:   description = "Aleph, première lettre"
```

**BDB3814** -- יְשַׁעְיָ֫הוּ "Isaiah" (nom propre -- majuscule accentuée **Ésaïe**)
```json
English:
{
    "head_word": "יְשַׁעְיָ֫הוּ",
    "pos": "proper name, masculine",
    "primary": null,
    "description": "Isaiah, son of Amos, the prophet",
    "senses": [
        {"number": 1, "primary": null, "description": "Isaiah, son of Amos, the prophet"},
        {"number": 2, "primary": null, "description": "one of the children of Jeduthun"},
        {"number": 3, "primary": null, "description": "a Levite ancestor of one of David's treasurers"}
    ]
}
French:
{
    "head_word": "יְשַׁעְיָ֫הוּ",
    "pos": "nom propre, masculin",
    "primary": null,
    "description": "Ésaïe, fils d'Amos, le prophète",
    "senses": [
        {"number": 1, "primary": null, "description": "Ésaïe, fils d'Amos, le prophète"},
        {"number": 2, "primary": null, "description": "un des enfants de Jeduthun"},
        {"number": 3, "primary": null, "description": "un ancêtre lévite d'un des trésoriers de David"}
    ]
}
```

**BDB883** -- בְאֵרִי "Esau's father-in-law" (majuscule accentuée **Ésaü**)
```json
English:
{
    "head_word": "בְאֵרִי",
    "pos": "proper name, masculine",
    "primary": null,
    "description": "a Hittite, Esau's father-in-law",
    "senses": [
        {"number": 1, "primary": null, "description": "a Hittite, Esau's father-in-law"},
        {"number": 2, "primary": null, "description": "Hosea's father"}
    ]
}
French:
{
    "head_word": "בְאֵרִי",
    "pos": "nom propre, masculin",
    "primary": null,
    "description": "un Hittite, beau-père d'Ésaü",
    "senses": [
        {"number": 1, "primary": null, "description": "un Hittite, beau-père d'Ésaü"},
        {"number": 2, "primary": null, "description": "père d'Osée"}
    ]
}
```

**BDB9249** -- תִּרְהָקָה "Ethiopian Dynasty" (majuscule accentuée **Égypte**, **Éthiopienne**)
```json
English:
{
    "head_word": "תִּרְהָקָה",
    "pos": "proper name, masculine",
    "primary": null,
    "description": "king of Egypt, of Ethiopian Dynasty:",
    "senses": []
}
French:
{
    "head_word": "תִּרְהָקָה",
    "pos": "nom propre, masculin",
    "primary": null,
    "description": "roi d'Égypte, de la dynastie éthiopienne :",
    "senses": []
}
```

**BDB1233** -- ֵבּלְאשַׁצַּר (description en prose complète -- **tout** traduire)
```json
English:
{
    "head_word": "ֵבּלְאשַׁצַּר",
    "pos": "proper name, masculine",
    "primary": null,
    "description": "represented as\n    king of Babylon, successor, and apparent son of Nebuchadrezzar",
    "senses": []
}
French:
{
    "head_word": "ֵבּלְאשַׁצַּר",
    "pos": "nom propre, masculin",
    "primary": null,
    "description": "présenté comme roi de Babylone, successeur et fils apparent de Nabuchodonosor",
    "senses": []
}
```

**BDB1553** -- גּוֺזָן (description géographique -- **tout** traduire, y compris prépositions)
```json
English:
{
    "head_word": "גּוֺזָן",
    "pos": "proper name [of a location]",
    "primary": null,
    "description": "city and district of Mesopotamia, on or near the middle\n    course of the Euphrates",
    "senses": []
}
French:
{
    "head_word": "גּוֺזָן",
    "pos": "nom propre [d'un lieu]",
    "primary": null,
    "description": "ville et district de Mésopotamie, sur ou près du cours moyen de l'Euphrate",
    "senses": []
}
```

### Exemples HTML (Entries/ -> Entries_fr/, balises retirées)

Ces exemples montrent le contenu textuel lisible résultant de la traduction du
HTML **dans leur intégralité** -- aucune partie n'est omise. Dans les fichiers
réels, les balises XML (`<pos>`, `<primary>`, `<bdbheb>`, `<ref>`, etc.) doivent
être préservées -- seul le texte anglais entre les balises est traduit.

**BDB1** -- א Aleph (entrée complète avec renvoi)
```
English:
  Biblical Hebrew
  א, Aleph, first letter; in post Biblical Hebrew = numeral 1
  (and so in margin of printed MT); א֟ = 1000; no evidence of
  this usage in OT times.
  ---
  אָב see II. אבה.

French:
  hébreu biblique
  א, Aleph, première lettre ; en hébreu post-biblique = chiffre 1
  (ainsi en marge du TM imprimé) ; א֟ = 1000 ; aucune trace de
  cet usage à l'époque de l'AT.
  ---
  אָב voir II. אבה.
```

**BDB50** -- אָבַל mourn (entrée complète, trois thèmes verbaux)
```
English:
  Biblical Hebrew
  I. אָבַל  verb  mourn  (Assyrian [abâlu] see Dl) --
  Qal  Perfect אָבַל Isa 24:7 + 2 t. etc.  Imperfect 3 feminine
  singular תֶּאֱבַל Hos 4:3 + 3 t. --  mourn, lament (poetic &
  higher style); absolute, human subject Joel 1:9; Amos 8:8;
  Amos 9:5; Isa 19:8 (|| אנה) compare Job 14:22 (subject נַפְשׁוֺ);
  followed by על Hos 10:5 more often figurative, inanimate subject,
  gates 1Sam 3:26 land 1Sam 24:4; 1Sam 33:9; Hos 4:3; Joel 1:10;
  Jer 4:28 (followed by על) Jer 12:4; Jer 23:10 compare Jer 12:11
  (followed by על), יְהוּדָה Jer 14:2 pastures Amos 1:2.
  Hithpa`el -- Perfect הִתְאַבֵּל 1Sam 15:35  Imperfect יִתְאַבָּ֑ל
  Ezek 7:12; Ezek 7:27  וַיִּתְאַבֵּל Gen 37:34 + 3 t. etc.;
  Imperative feminine singular הִתְאַבְּלִי 2Sam 14:2  Participle
  מִתְאַבֵּל 1Sam 16:1 + 2 t. etc.; -- mourn (mostly prose)
  especially for dead, followed by על Gen 37:34; 2Sam 13:37;
  2Sam 14:2; 2Sam 19:2 || בכה 2Chr 35:24, compare also Isa 66:10
  (over Jerusalem); absolute 1Chr 7:22 compare 2Sam 14:2 play the
  mourner (where indicated by dress); over un-worthy Saul followed
  by אֶל 1Sam 15:35; 1Sam 16:1 over sin followed by על Ezra 10:6
  compare (absolute) Neh 8:9 judgment of ׳ י Exod 33:4 absolute
  (indicated by dress), Num 14:39; Ezek 7:27 (strike out B Co);
  followed by כִּי 1Sam 6:19 calamity Neh 1:4; Ezek 7:12 compare
  Dan 10:2.
  Hiph`il  Perfect הֶאֱבַלְתִּי Ezek 31:15  Imperfect וַיַּאֲבֶלֿ
  Lam 2:8 -- cause to mourn; Ezek 31:15 absolute MT, but A B Co
  object תהום followed by על, caused the deep to mourn over;
  Lam 2:8 object wall etc.; (both these figurative, compare Qal).

French:
  hébreu biblique
  I. אָבַל  verbe  être en deuil  (assyrien [abâlu] voir Dl) --
  Qal  Parfait אָבַל Es 24,7 + 2 t. etc.  Imparfait 3 féminin
  singulier תֶּאֱבַל Os 4,3 + 3 t. --  être en deuil, se lamenter
  (poétique & style élevé) ; absolu, sujet humain Jl 1,9 ; Am 8,8 ;
  Am 9,5 ; Es 19,8 (|| אנה) comparer Jb 14,22 (sujet נַפְשׁוֺ) ;
  suivi de על Os 10,5 plus souvent figuré, sujet inanimé, portes
  1 S 3,26 terre 1 S 24,4 ; 1 S 33,9 ; Os 4,3 ; Jl 1,10 ;
  Jr 4,28 (suivi de על) Jr 12,4 ; Jr 23,10 comparer Jr 12,11
  (suivi de על), יְהוּדָה Jr 14,2 pâturages Am 1,2.
  Hithpa`el -- Parfait הִתְאַבֵּל 1 S 15,35  Imparfait יִתְאַבָּ֑ל
  Ez 7,12 ; Ez 7,27  וַיִּתְאַבֵּל Gn 37,34 + 3 t. etc. ;
  Impératif féminin singulier הִתְאַבְּלִי 2 S 14,2  Participe
  מִתְאַבֵּל 1 S 16,1 + 2 t. etc. ; -- être en deuil (surtout prose)
  surtout pour les morts, suivi de על Gn 37,34 ; 2 S 13,37 ;
  2 S 14,2 ; 2 S 19,2 || בכה 2 Ch 35,24, comparer aussi Es 66,10
  (concernant Jérusalem) ; absolu 1 Ch 7,22 comparer 2 S 14,2 jouer
  l'endeuillé (quand indiqué par le vêtement) ; sur l'indigne Saül
  suivi de אֶל 1 S 15,35 ; 1 S 16,1 sur le péché suivi de על
  Esd 10,6 comparer (absolu) Ne 8,9 jugement de ׳ י Ex 33,4 absolu
  (indiqué par le vêtement), Nb 14,39 ; Ez 7,27 (supprimer B Co) ;
  suivi de כִּי 1 S 6,19 calamité Ne 1,4 ; Ez 7,12 comparer
  Dn 10,2.
  Hiphil  Parfait הֶאֱבַלְתִּי Ez 31,15  Imparfait וַיַּאֲבֶלֿ
  Lm 2,8 -- faire porter le deuil ; Ez 31,15 absolu TM, mais A B Co
  objet תהום suivi de על, a fait porter le deuil à l'abîme sur ;
  Lm 2,8 objet muraille etc. ; (tous deux figurés, comparer Qal).
```

**BDB200** -- אוּלָם nom propre (entrée complète)
```
English:
  Biblical Hebrew
  II. אוּלָם  proper name, masculine  only genealogy
  1. 1Chr 7:16; 1Chr 7:17.
  2. 1Chr 8:39; 1Chr 8:40.

French:
  hébreu biblique
  II. אוּלָם  nom propre, masculin  seulement généalogie
  1. 1 Ch 7,16 ; 1 Ch 7,17.
  2. 1 Ch 8,39 ; 1 Ch 8,40.
```

### Exemples HTML avec majuscules accentuées

Ces exemples illustrent spécifiquement les cas où le français exige un accent
sur une lettre majuscule -- un nom propre ou le premier mot d'une phrase.

**BDB3814** -- יְשַׁעְיָ֫הוּ **Ésaïe** (entrée complète, sans placeholder)
```
English:
  Biblical Hebrew
  יְשַׁעְיָ֫הוּ  proper name, masculine (salvation of Yah; compare
  אֱלִישָׁע above; ישעאל on scarab ClGann) --
  1. Isaiah, son of Amos, the prophet: Isa 1:1 + 15 t. Isaiah;
     2Kgs 19:2 + 12 t. Kings; 2Chr 26:22; 2Chr 32:20; 2Chr 32:32
     ᵐ5 Ηξαιας, ᵑ9 Isaias.
  2. one of the children of Jeduthun 1Chr 25:3; 1Chr 25:15,
     ᵐ5 Ισαια, etc.
  3. a Levite ancestor of one of David's treasurers 1Chr 26:25,
     ᵐ5 Ωσαιας, ᵐ5L Ιωσηε.

French:
  hébreu biblique
  יְשַׁעְיָ֫הוּ  nom propre, masculin (salut de Yah ; comparer
  אֱלִישָׁע ci-dessus ; ישעאל sur scarabée ClGann) --
  1. Ésaïe, fils d'Amos, le prophète : Es 1,1 + 15 t. Ésaïe ;
     2 R 19,2 + 12 t. Rois ; 2 Ch 26,22 ; 2 Ch 32,20 ; 2 Ch 32,32
     ᵐ5 Ηξαιας, ᵑ9 Isaias.
  2. un des enfants de Jeduthun 1 Ch 25,3 ; 1 Ch 25,15,
     ᵐ5 Ισαια, etc.
  3. un ancêtre lévite d'un des trésoriers de David 1 Ch 26,25,
     ᵐ5 Ωσαιας, ᵐ5L Ιωσηε.
```

**BDB883** -- בְאֵרִי beau-père d'**Ésaü** (entrée complète, sans placeholder)
```
English:
  Biblical Hebrew
  בְאֵרִי  proper name, masculine (my well).
  < the man from Beer? Nes.
  1. a Hittite, Esau's father-in-law Gen 26:34.
  2. Hosea's father Hos 1:1.

French:
  hébreu biblique
  בְאֵרִי  nom propre, masculin (mon puits).
  < l'homme de Beer ? Nes.
  1. un Hittite, beau-père d'Ésaü Gn 26,34.
  2. père d'Osée Os 1,1.
```

**BDB9249** -- תִּרְהָקָה roi d'**Égypte** (entrée complète, sans placeholder)
```
English:
  Biblical Hebrew
  תִּרְהָקָה  proper name, masculine  king of Egypt, of Ethiopian
  Dynasty: 2Kgs 19:9 = Isa 37:9 Θαρακα; ᵐ5L Θαρθακ; = Egyptian
  T-h-r-‡, Assyrian Tar‡u, Steind COT Wied Brugsch WMM Griffith.
  ---
  תְּרוּמָה, תְּרוּמִיָּה see רום. תְּרוּעָה see [רוע].
  ---
  תְּרוּפָה see רוף.

French:
  hébreu biblique
  תִּרְהָקָה  nom propre, masculin  roi d'Égypte, de la dynastie
  éthiopienne : 2 R 19,9 = Es 37,9 Θαρακα ; ᵐ5L Θαρθακ ; = égyptien
  T-h-r-‡, assyrien Tar‡u, Steind COT Wied Brugsch WMM Griffith.
  ---
  תְּרוּמָה, תְּרוּמִיָּה voir רום. תְּרוּעָה voir [רוע].
  ---
  תְּרוּפָה voir רוף.
```

### Mots et expressions courants exigeant des accents

Ces termes apparaissent fréquemment dans les entrées BDB. Toujours utiliser
la forme accentuée :

```
Anglais              Français correct       FAUX (sans accents)
-------              ----------------       -------------------
to be                être                   etre
elevated, raised     élevé                  eleve
sword                épée                   epee
worn out             usé                    use
grain, wheat         blé                    ble
father               père                   pere
mother               mère                   mere
summer               été                    ete
born                 né                     ne
desired              désiré                 desire
separated            séparé                 separe
crushed              écrasé                 ecrase
consecrated          consacré               consacre
blessed              béni                   beni
created              créé                   cree
first (fem.)         première               premiere
freshness            fraîcheur              fraicheur
abyss                abîme                  abime
i.e.                 c.-à-d.               c.-a-d.
perhaps              peut-être              peut-etre
feminine             féminin                feminin
genealogy            généalogie             genealogie
poetic               poétique               poetique
```

### Traduction des références bibliques

Les noms de livres bibliques doivent être convertis des abréviations anglaises
vers leurs équivalents français standard. Le format chapitre:verset reste le
même ; seul le nom du livre change. Dans les balises HTML `<ref>`, mettre à
jour le texte affiché mais laisser les attributs `ref`, `b`, `cBegin`,
`vBegin`, etc. inchangés.

Correspondances standard (anglais -> français) :

```
Gen  -> Gn       Exod -> Ex       Lev  -> Lv       Num  -> Nb
Deut -> Dt       Josh -> Jos      Judg -> Jg       Ruth -> Rt
1Sam -> 1 S      2Sam -> 2 S      1Kgs -> 1 R      2Kgs -> 2 R
1Chr -> 1 Ch     2Chr -> 2 Ch     Ezra -> Esd      Neh  -> Ne
Esth -> Est      Job  -> Jb       Ps   -> Ps       Prov -> Pr
Eccl -> Qo       Song -> Ct       Isa  -> Es       Jer  -> Jr
Lam  -> Lm       Ezek -> Ez       Dan  -> Dn       Hos  -> Os
Joel -> Jl       Amos -> Am       Obad -> Ab       Jonah -> Jon
Mic  -> Mi       Nah  -> Na       Hab  -> Ha       Zeph -> So
Hag  -> Ag       Zech -> Za       Mal  -> Ml
```

Formes développées courantes dans le BDB :
```
Genesis     -> Genèse         Exodus      -> Exode
Leviticus   -> Lévitique      Numbers     -> Nombres
Deuteronomy -> Deutéronome    Joshua      -> Josué
Judges      -> Juges          Samuel      -> Samuel
Kings       -> Rois           Chronicles  -> Chroniques
Nehemiah    -> Néhémie        Esther      -> Esther
Psalms      -> Psaumes        Proverbs    -> Proverbes
Ecclesiastes -> Qohéleth      Song of Solomon -> Cantique des Cantiques
Isaiah      -> Ésaïe          Jeremiah    -> Jérémie
Lamentations -> Lamentations  Ezekiel     -> Ézéchiel
Daniel      -> Daniel         Hosea       -> Osée
Obadiah     -> Abdias         Jonah       -> Jonas
Micah       -> Michée         Nahum       -> Nahoum
Habakkuk    -> Habacuc        Zephaniah   -> Sophonie
Haggai      -> Aggée          Zechariah   -> Zacharie
Malachi     -> Malachie
```

### Ce qu'il ne faut PAS traduire

- Le texte hébreu et araméen (tout ce qui est en écriture de droite à gauche)
- Les numéros Strong ("H8532")
- Les identifiants d'entrée BDB ("BDB10000")
- Les codes d'abréviation savante apparaissant en ligne
- Les attributs des balises `<ref>` (`ref`, `b`, `cBegin`, `vBegin`, etc.)
- Les numéros de chapitre et de verset dans les références

## Flux de travail

### Pipeline de traduction HTML (en 4 étapes)

La traduction des entrées HTML suit un pipeline en 4 étapes. Des instances
Claude distinctes peuvent travailler sur différentes étapes ou tranches.

```
Entries/  --[script]--> Entries_txt/  --[LLM]--> Entries_txt_fr/  --[LLM]--> Entries_fr/
                                                                       |
                                                                  [script: validate]
```

**Étape 1 : Extraction** (`scripts/extract_txt.py`, déterministe)
Convertit chaque fichier HTML en texte brut lisible. Les balises sont retirées,
sauf les placeholders qui deviennent `[placeholder8: Placeholders/8.gif]` pour
que le traducteur puisse consulter l'image du mot apparenté. Le texte
hébreu/araméen, les abréviations savantes et les références bibliques sont
préservés en ligne. Résultat dans `Entries_txt/`.

```
python3 scripts/extract_txt.py              # tout extraire
python3 scripts/extract_txt.py BDB17        # une seule entrée
```

**Étape 2 : Traduction** (LLM, `Entries_txt/` -> `Entries_txt_fr/`)
Un LLM traduit chaque fichier `.txt` de l'anglais vers le français. C'est
l'étape qui exige le modèle le plus capable. Le texte en entrée est propre,
sans balisage, ce qui facilite une traduction de haute qualité. Toutes les
règles de traduction (accents, noms bibliques, catégories grammaticales, etc.)
décrites dans ce fichier s'appliquent.

**Étape 3 : Réassemblage** (LLM, `Entries/` + `Entries_txt_fr/` -> `Entries_fr/`)
Un LLM (potentiellement moins puissant) reçoit le HTML anglais original et le
texte français traduit, puis produit le HTML français en réinsérant les balises.
C'est du pattern matching -- remplacer le texte anglais par son équivalent
français tout en préservant la structure des balises.

**⚠️ PIÈGE CONNU — ne pas confondre « réassemblage » avec « copie » ⚠️**

Le mot « réassemblage » peut induire en erreur : il ne s'agit PAS de copier le
HTML anglais dans `Entries_fr/`. L'objectif est de produire un fichier HTML
**en français** — chaque fragment de texte anglais entre les balises doit être
remplacé par son équivalent français tiré de `Entries_txt_fr/`.

Concrètement, vous avez trois entrées :

| Fichier | Rôle |
|---|---|
| `Entries/BDBnnn.html` | fournit la **structure des balises** |
| `Entries_txt_fr/BDBnnn.txt` | fournit le **texte français** à insérer |
| `Entries_txt/BDBnnn.txt` | (optionnel) aide à localiser quel texte anglais correspond à quel texte français |

Et une sortie : `Entries_fr/BDBnnn.html` — le HTML avec balises préservées et
texte en français.

Exemple concret — BDB50, un extrait :

```
Entrée HTML anglaise :  <pos>verb</pos> … <primary>mourn</primary>
Texte français (txt_fr): verbe … être en deuil
Sortie HTML française :  <pos>verbe</pos> … <primary>être en deuil</primary>
```

❌ **Erreur type** : écrire `<pos>verb</pos> … <primary>mourn</primary>` dans
`Entries_fr/` — c'est une copie de l'anglais, pas une traduction.

**Auto-vérification** : parcourez votre sortie HTML. Si vous y voyez du texte
anglais (hors abréviations savantes dans `<lookup>` et noms propres), le
fichier est incorrect — recommencez en utilisant le texte de `Entries_txt_fr/`.

**Étape 4 : Validation** (`scripts/validate_html.py`, déterministe)
Vérifie que le HTML français contient tous les éléments préservés de l'original
(hébreu, placeholders, attributs ref, abréviations) et que le texte français
de l'étape 2 apparaît dans le résultat.

Cette étape est exécutée **en lot après que tous les travailleurs ont terminé**,
pas par chaque agent individuellement. Les agents de l'étape 3 doivent produire
leurs fichiers `Entries_fr/` et passer à l'entrée suivante — la validation et
la correction des erreurs se font dans une passe séparée.

```
python3 scripts/validate_html.py            # tout valider
python3 scripts/validate_html.py BDB17      # une seule entrée
python3 scripts/validate_html.py --summary  # totaux seulement
```

### Consultation des images Placeholders

Dans les fichiers `Entries_txt/`, les placeholders apparaissent sous la forme :
```
[placeholder8: Placeholders/8.gif]
```
Le chemin est relatif à la racine du projet. Pour voir l'image du mot apparenté
(arabe, syriaque, éthiopien, etc.), ouvrir le fichier GIF correspondant. Cela
peut aider à comprendre le contexte étymologique lors de la traduction.

Le fichier `placeholders.csv` associe chaque numéro à sa langue source et son
contexte HTML d'origine.

### Script utilitaire : `scripts/untranslated.py`

Affiche les fichiers qui restent à traduire. Vérifie trois étapes du pipeline :

1. **`--txt`** : `Entries_txt/` contre `Entries_txt_fr/` (étape 2 -- traduction)
2. **`--html`** : `Entries/` contre `Entries_fr/` (étape 3 -- réassemblage HTML).
   N'affiche que les entrées dont les prérequis existent (le `.txt` et le
   `.txt_fr` correspondants). Les entrées en attente de traduction txt_fr sont
   comptées séparément comme « awaiting txt_fr ».
3. **`--json`** : `json_output/` contre `json_output_fr/`

Sans filtre `--txt`/`--html`/`--json`, les trois sont affichés.

Le script requiert un ou plusieurs **arguments numériques** (0-9) qui filtrent
les entrées par le dernier chiffre du numéro BDB. Cela permet à 10 travailleurs
de traduire le corpus en parallèle sans chevauchement.

```
python3 scripts/untranslated.py 0            # entrées finissant par 0
python3 scripts/untranslated.py 1 5          # entrées finissant par 1 ou 5
python3 scripts/untranslated.py 0 1 2 3 4 5 6 7 8 9   # tout
python3 scripts/untranslated.py 3 -n 5       # afficher 5, finissant par 3
python3 scripts/untranslated.py 7 --json     # json seulement, finissant par 7
python3 scripts/untranslated.py 2 --txt      # txt seulement, finissant par 2
python3 scripts/untranslated.py 9 --html     # html seulement, finissant par 9
python3 scripts/untranslated.py 4 --count    # totaux seuls, finissant par 4
python3 scripts/untranslated.py 5 --txt --html --json -n 5  # les trois, 5 par mode
```

Format de sortie pour `--html` (montre les 3 fichiers d'entrée nécessaires) :
```
Entries_fr (ending in 0): 50/1002 translated, 800 ready, 152 awaiting txt_fr
  ./Entries/BDB10.html + ./Entries_txt/BDB10.txt + ./Entries_txt_fr/BDB10.txt => ./Entries_fr/BDB10.html
```

Sans arguments, le script affiche l'aide. Code de sortie 0 quand la tranche
est entièrement traduite, 1 quand des fichiers restent, 2 en cas d'arguments
invalides.

Exemple de partitionnement (10 travailleurs) :
- Travailleur A : `scripts/untranslated.py 0`  (~1 002 entrées)
- Travailleur B : `scripts/untranslated.py 1`  (~1 002 entrées)
- ...
- Travailleur J : `scripts/untranslated.py 9`  (~1 002 entrées)

### Flux de traduction JSON

La conversion se fait par lots. Un LLM lit chaque fichier de `json_output/`,
traduit les champs anglais pertinents (y compris les noms de livres bibliques
dans `description` et `senses[].description`), et écrit le résultat dans
`json_output_fr/` avec le même nom de fichier. Le JSON est assez simple pour
ne pas nécessiter le pipeline d'extraction intermédiaire.

### Balises HTML et leur traitement

Lors du réassemblage (étape 3), ces balises doivent être traitées comme suit :
- `<pos>...</pos>` -- traduire le contenu (catégorie grammaticale)
- `<primary>...</primary>` -- traduire le contenu (glose)
- `<highlight>...</highlight>` -- traduire le contenu
- `<descrip>...</descrip>` -- traduire le contenu
- `<meta>...</meta>` -- traduire le contenu (termes grammaticaux)
- `<language>...</language>` -- traduire le contenu ("Biblical Aramaic" -> "araméen biblique")
- `<bdbheb>...</bdbheb>` -- garder tel quel (hébreu)
- `<bdbarc>...</bdbarc>` -- garder tel quel (araméen)
- `<entry>...</entry>` -- garder tel quel (identifiants)
- `<ref ...>...</ref>` -- garder les attributs, traduire le texte affiché (nom du livre)
- `<lookup ...>...</lookup>` -- garder tel quel (abréviations savantes)
- `<transliteration>...</transliteration>` -- garder tel quel
- `<reflink>...</reflink>` -- garder tel quel
- `<placeholder*>` -- garder tel quel (images de scripts apparentés ; voir Placeholders ci-dessous)
- `<checkingNeeded />`, `<wrongReferenceRemoved />` -- garder tel quel

## Placeholders (images de scripts de langues apparentées)

Le lexique BDB original cite fréquemment des mots apparentés d'autres langues
sémitiques -- arabe, syriaque, éthiopien (guèze), nabatéen, assyrien, etc. --
pour illustrer les liens étymologiques. Lors de la numérisation du lexique, ces
écritures non hébraïques ne pouvaient pas être représentées en Unicode (ou
l'outillage de l'époque ne le permettait pas), et chaque mot apparenté a donc
été sauvegardé comme une petite image GIF dans `Placeholders/` (numérotées de
`1.gif` à `6200.gif`, ~6 200 au total).

Dans les entrées HTML, ces images apparaissent comme des balises auto-fermantes
telles que `<placeholder1 />`, `<placeholder6192 />`, etc. Le numéro correspond
au nom du fichier GIF. Par exemple, `<placeholder8 />` dans BDB17 (l'entrée
pour אָב « père ») est une image du mot arabe apparenté **أَبٌ** (« père »).

Le fichier `placeholders.csv` associe chaque numéro de placeholder à :
- la langue source supposée (arabe, syriaque, éthiopien, etc.)
- l'entrée BDB à laquelle il appartient
- un extrait du contexte HTML environnant

### Traitement en traduction

Les balises placeholder **ne sont pas du contenu traduisible**. Ce sont des
références opaques à des images de scripts. Lors de la traduction :

- **HTML** : Copier chaque balise `<placeholder* />` telle quelle à sa position
  exacte. Ne pas les supprimer, renuméroter ou modifier. Elles font partie de
  l'appareil savant, pas du texte anglais.
- **JSON** : Les balises placeholder n'apparaissent pas dans les fichiers JSON
  (l'extraction JSON les a retirées), elles ne concernent donc que la
  traduction HTML.
- **Texte anglais environnant** : Les mots anglais autour d'un placeholder
  (p. ex. "Arabic `<placeholder7 />`, Assyrian ...") doivent être traduits en
  français ("arabe `<placeholder7 />`, assyrien ...") mais la balise elle-même
  reste inchangée.

## Entrées squelettiques (fichiers vides)

872 entrées (~8,7 %) n'ont aucun contenu traduisible : `pos`, `primary` et
`description` sont tous `null` et `senses` est `[]`. Le seul champ non nul est
`head_word`. Il s'agit généralement de stubs de redirection ou de racines
servant de repères dans la structure du dictionnaire, sans définition.

Ces entrées ont été prétraitées en créant des **fichiers de zéro octet** dans
`json_output_fr/` afin que `untranslated.py` les ignore. Pour les retrouver :

```bash
find json_output_fr/ -empty -name '*.json'   # lister les placeholders vides
find json_output_fr/ -empty | wc -l          # les compter (872 attendus)
```

**Ne pas** écrire de contenu dans ces fichiers. Si une entrée squelettique
acquiert ultérieurement du contenu dans la source anglaise, supprimer le fichier
vide et traduire normalement.

## Noms de langues

Les descriptions du BDB mentionnent fréquemment des langues apparentées.
Elles doivent être traduites de manière cohérente :

```
Anglais              Français
-------              --------
Arabic               arabe
Assyrian             assyrien
Biblical Aramaic     araméen biblique
Biblical Hebrew      hébreu biblique
Ethiopic             éthiopien
Late Hebrew          hébreu tardif
Mandean              mandéen
Nabataean            nabatéen
New Hebrew           néo-hébreu
Old Aramaic          ancien araméen
Palmyrene            palmyrénien
Phoenician           phénicien
Sabean / Sabaean     sabéen
Syriac               syriaque
Targum               targoum
```

La balise `<language>` dans les entrées HTML n'a que deux valeurs : "Biblical
Hebrew" et "Biblical Aramaic". Les traduire respectivement par « hébreu
biblique » et « araméen biblique ».

## Renvois

~400 entrées contiennent des renvois dans `description` comme "see בחון above"
ou "compare גִּלְגָּל". Traduire la structure anglaise mais préserver le mot
hébreu et toute référence à une entrée BDB :

```
Schéma anglais               Schéma français
--------------               ---------------
see X above                  voir X ci-dessus
see X below                  voir X ci-dessous
see X                        voir X
compare X                    comparer X
which see                    q.v.
```

## Noms de thèmes verbaux

Les thèmes verbaux hébreux apparaissent tout au long du BDB. Ce sont des
translittérations conventionnelles utilisées également en exégèse biblique
francophone -- les conserver tels quels :

- Qal, Niph'al (Niphal), Pi'el (Piel), Pu'al (Pual)
- Hiph'il (Hiphil), Hoph'al (Hophal), Hithpa'el (Hithpael)

Les étiquettes anglaises environnantes doivent être traduites :
- "Qal Perfect" -> "Qal Parfait"
- "Hiph'il Imperfect" -> "Hiphil Imparfait"
- "Niph'al Participle" -> "Niphal Participe"
- "Infinitive construct" -> "Infinitif construit"
- "Infinitive absolute" -> "Infinitif absolu"

## Abréviations savantes

Le BDB utilise ~337 codes d'abréviation uniques pour les auteurs, les revues et
les versions anciennes (p. ex. Dl, Dr, Bev, Kau, Tg, Aq, Symm, Theod). Ceux-ci
apparaissent dans les balises `<lookup>` en HTML et parfois en ligne dans les
descriptions JSON. **Ne jamais les traduire.** Ce sont des références
standardisées à des ouvrages savants, indépendantes de la langue. Les préserver
exactement, y compris toute notation en exposant.

## Sauts de ligne intégrés

~10 % des entrées contiennent des caractères `\n` dans les champs `pos`,
`primary` ou `description` -- artefacts de l'extraction HTML-vers-JSON. Lors de
la traduction :

- Supprimer les espaces en début/fin et réduire les séquences de `\n` + espaces
  en un seul espace, sauf si le saut de ligne sépare clairement des éléments
  distincts.
- Exception : si un champ `pos` contient un paragraphe entier de notes d'usage
  (p. ex. BDB2204), ne traduire que l'étiquette grammaticale au début et
  préserver le reste comme contenu de type `description`. Signaler ces cas pour
  révision.

## Champs `pos` débordants

Un petit nombre d'entrées (~2) ont des valeurs `pos` qui débordent en notes
d'usage complètes ou en définitions (centaines de caractères avec de l'hébreu
intégré, des références et de la prose). Pour celles-ci :

- Extraire et traduire uniquement l'étiquette grammaticale (p. ex. "adverb or
  interjection" -> "adverbe ou interjection").
- Le contenu excédentaire appartient sémantiquement à `description`. Dans la
  sortie française, le déplacer là si possible, ou le préserver dans `pos` avec
  un commentaire signalant l'irrégularité.

## Méthode de traduction obligatoire — INTERDICTION DE SCRIPTS

**Chaque entrée doit être traduite individuellement par le LLM.** Il est
**strictement interdit** d'écrire des scripts de remplacement par motifs (sed,
awk, dictionnaire Python, boucle avec `str.replace()`, expressions régulières,
etc.) pour traduire en masse ou partiellement. Les seuls scripts autorisés à **exécuter** sont
ceux du répertoire `scripts/` (extraction, validation, liste des fichiers non
traduits). Ne jamais modifier, créer ou supprimer de fichiers dans `scripts/`
sauf si l'utilisateur le demande explicitement.

La traduction exige une compréhension contextuelle du texte anglais victorien —
un simple rechercher-remplacer ne suffit pas et produit du « franglais »
inutilisable. Voici des exemples réels de ce qu'un script produit :

```
❌ Script : "represented as roi de Babylone, successor, and apparent fils de Nebuchadrezzar"
❌ Script : "city and district of Mesopotamia, on or près de the middle course of the Euphrates"
❌ Script : "ville en the tribe of Simeon"
✅ LLM :    "présenté comme roi de Babylone, successeur et fils apparent de Nabuchodonosor"
✅ LLM :    "ville et district de Mésopotamie, sur ou près du cours moyen de l'Euphrate"
✅ LLM :    "ville dans la tribu de Siméon"
```

Si vous constatez que votre sortie contient un mélange d'anglais et de français,
c'est le signe que vous avez utilisé une approche par motifs au lieu de traduire
le texte. Arrêtez-vous et recommencez en traduisant la phrase entière.

## Traduction intégrale — pas de « franglais »

Chaque champ `description`, `primary` et `senses[].description` doit être
**intégralement en français** — y compris les prépositions, articles et mots de
liaison (of, the, and, in, at, on, or, with, from, etc.). Voir les exemples
BDB1233 et BDB1553 ci-dessus pour le traitement correct des descriptions en
prose complète. Après avoir écrit un champ, relisez-le : s'il contient un mot
anglais courant qui n'est pas une abréviation savante ou un nom propre
invariable, corrigez-le.

## Notes de qualité

- Le texte original du BDB est en anglais de l'époque victorienne. Le français
  doit être moderne, accessible et précis -- pas un calque mot à mot. Viser le
  registre d'un ouvrage de référence contemporain en études bibliques
  francophones.
- **Toujours utiliser les accents et diacritiques français corrects**, y compris
  sur les majuscules. Voir la section « Accents et UTF-8 » ci-dessus et le
  tableau des mots courants. Écrire « être », « féminin », « Néhémie »,
  « Ésaïe », « À partir de ».
- Le style français de référence biblique utilise une virgule entre chapitre et
  verset (p. ex. « Dn 7,5 » et non « Dn 7:5 »), conformément à la convention
  de la Bible de Jérusalem et de la TOB.
- Le schéma JSON est cohérent pour les 10 022 entrées : chaque élément de
  `senses` a exactement `{number, primary, description}`. Il n'existe pas de
  structures imbriquées ou variantes.
