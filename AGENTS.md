# Brown-Driver-Briggs Enhanced -- Projet de lexique français

**Rôle de l'agent :** Vous êtes un traducteur expert spécialisé en hébreu
biblique, araméen, anglais victorien et exégèse francophone. Votre tâche est de
traduire le lexique BDB vers un français académique, moderne et rigoureux, sans
jamais altérer les données sources hébraïques ou les balises structurelles.

## État actuel et tâches en cours

Voir `doc/todo.md` pour la liste détaillée des tâches (actuellement centrée sur
llm_verify et la correction des traductions signalées). Après chaque étape
terminée, mettre à jour `doc/todo.md` et passer à l'étape suivante sauf
instruction contraire.

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
    Entries_notes/      # Notes de revue des erreurs signalées par llm_verify
    json_output/        # JSON anglais, un fichier par entrée BDB (source)
    json_output_fr/     # JSON français, un fichier par entrée BDB (cible)
    Placeholders/       # ~6 200 images GIF de scripts de langues apparentées
    doc/                # Documentation du projet (todo.md, analyses, etc.)
    scripts/            # Outils du pipeline de traduction
        extract_txt.py  # Entries/ -> Entries_txt/ (extraction déterministe)
        validate_html.py # Vérification de Entries_fr/ contre originaux
        untranslated.py # Liste les fichiers non encore traduits
        llm_verify.py   # Vérification par LLM local des traductions txt_fr
        review_errors.py # Liste les entrées signalées non encore revues
        check_hebrew.py # Vérifie la préservation du texte hébreu/araméen
    test/               # Tests pour les scripts (check_hebrew, validate_html, etc.)
    llm_verify_txt_results.txt  # Résultats de vérification LLM des Entries_txt_fr/
    bdbToStrongsMapping.csv
    placeholders.csv
    AGENTS.md           # Ce fichier (symlinké comme CLAUDE.md et GEMINI.md)
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
- « épée » et non « epee », « été » et non « ete », « né » et non « ne »
- « consacré » et non « consacre », « créé » et non « cree », « abîme » et non « abime »
- « père » et non « pere », « mère » et non « mere », « peut-être » et non « peut-etre »
- « fraîcheur » et non « fraicheur », « première » et non « premiere »
- « À partir de » et non « A partir de », « État » et non « Etat »

Pour les majuscules accentuées sur les noms propres (Ésaïe, Égypte, etc.),
voir la section « Traduction des noms propres et lieux ».

Tous les fichiers de sortie (JSON et HTML) sont en UTF-8. Chaque caractère
accentué (é, è, ê, ë, à, â, ù, û, ô, î, ï, ç, etc.) doit apparaître comme
le codepoint Unicode réel, jamais comme une entité HTML et jamais réduit à
l'ASCII.

**Typographie française :** Respecter les espaces avant les ponctuations doubles
(`;`, `:`, `?`, `!`) et à l'intérieur des guillemets (`« texte »`). Ne pas
utiliser le formatage anglais (*FAUX : « prophète: Es 1,1 » / CORRECT :
« prophète : Es 1,1 »*).

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

**BDB3814** -- יְשַׁעְיָ֫הוּ "Isaiah" (exemple complet avec `senses` et majuscule accentuée)
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

Autres exemples de traduction intégrale de descriptions :

**BDB1233** -- ֵבּלְאשַׁצַּר (prose complète -- **tout** traduire)
```
English:  description = "represented as king of Babylon, successor, and apparent son of Nebuchadrezzar"
French:   description = "présenté comme roi de Babylone, successeur et fils apparent de Nabuchodonosor"
```

**BDB1553** -- גּוֺזָן (géographique -- **tout** traduire, y compris prépositions)
```
English:  description = "city and district of Mesopotamia, on or near the middle course of the Euphrates"
French:   description = "ville et district de Mésopotamie, sur ou près du cours moyen de l'Euphrate"
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

### Anglais victorien — attention aux faux amis

Le BDB (1906) utilise un anglais victorien. Traduire d'après le contexte :
- **"corn"** = grain, céréale ou blé (PAS maïs).
- **"meat"** = nourriture en général (PAS viande, sauf si le contexte le précise).
- **"quick"** = vivant, chair vive (PAS rapide).
- **"sensible"** = perceptible par les sens ou avisé (PAS sensible au sens moderne).
- **"mire"** = boue, fange (PAS mire de visée).
- **"peculiar"** = propre à, particulier, spécifique (PAS étrange).
- **"discovery"** = révélation, exposition (PAS seulement découverte).
- **"contracted"** = abrégé, raccourci (PAS contracté physiquement).
- **"sign"** (verbe) = marquer, désigner (PAS signer un document).
- **"rule over"** = régner sur (PAS « dominer sur » — calque).

### Erreurs fréquentes à éviter

Ces erreurs ont été les plus courantes lors de la première passe de traduction
(identifiées par revue de ~1 000 entrées signalées) :

- **`&` → `et`** : Le BDB utilise `&` comme raccourci. En français, toujours
  écrire `et` dans le texte courant. Exception : dans les sigles savants
  (p. ex. `B & Co`), conserver tel quel.
- **`miles` → `milles`** : Unité de distance, toujours franciser.
- **Conventions de numérotation** : `1st` → `1ᵉʳ`, `2nd` → `2ᵉ`, `3rd` → `3ᵉ`,
  `ed.` → `éd.`
- **Abréviations savantes anglaises courantes** :
  `ff.` → `ss.`, `Eng. Tr.` → `trad. angl.`, `viz.` → `c.-à-d.`,
  `i.e.` → `c.-à-d.`, `e.g.` → `p. ex.` (`cf.` reste `cf.`)
- **Noms propres géographiques et ethniques** courants mal francisés :
  `Nephthali` → `Nephtali`, `Philadelphia` → `Philadelphie`,
  `Bashan` → `Basan`, `Cushite` → `Koushite`,
  `Gershonites` → `Guershonites`, `Esarhaddon` → `Assarhaddon`
- **Petits mots anglais oubliés** : Vérifier qu'aucun article (`a`, `an`,
  `the`), préposition (`in`, `of`, `on`, `for`) ou conjonction (`and`, `but`,
  `or`) anglais ne subsiste dans le texte français. C'est l'erreur la plus
  insidieuse — elle échappe à une relecture rapide.

### Traduction des noms propres et lieux

1. **Noms bibliques et lieux géographiques** : Doivent être traduits par leur
   équivalent français standard, **y compris les accents sur les majuscules**.
   - "Isaiah" -> "Ésaïe"
   - "Ezekiel" -> "Ézéchiel"
   - "Esau" -> "Ésaü"
   - "Egypt" -> "Égypte"
   - "Ephraim" -> "Éphraïm"
   - "Ephraimite" -> "Éphraïmite"
   - "Ethiopian" -> "Éthiopien"
   - "Moabite" -> "Moabite"
   - "Edomite" -> "édomite"
   - "Euphrates" -> "Euphrate"
   - "Judah" -> "Juda"

2. **Noms de savants modernes** (Robinson, Smith, Driver, etc.) : ne PAS
   traduire.

### Traduction des références bibliques

Les noms de livres bibliques doivent être convertis des abréviations anglaises
vers leurs équivalents français standard. Convertir les deux-points entre
chapitre et verset en virgule (ex : 7:5 -> 7,5). Dans les balises HTML `<ref>`, mettre à
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

**Préservation de la structure HTML :** Ne supprimez aucune balise HTML, même
si elle semble vide ou redondante. Le fichier `Entries_fr/` doit avoir la même
arborescence de balises que le fichier anglais original.

**Traduction `txt_fr` défectueuse :** Si vous constatez que le fichier
`Entries_txt_fr/` contient des erreurs évidentes (franglais, accents manquants,
texte anglais non traduit, faux ami victorien — voir « Erreurs fréquentes »),
**corrigez les deux fichiers** : d'abord `Entries_txt_fr/BDBnnn.txt` (le
source), puis utilisez la version corrigée pour produire `Entries_fr/`. Cela
garde les deux fichiers synchronisés et les corrections sont traçables via git.
Consignez le problème dans `errata-N.txt` (voir « Gestion des erreurs »).
Ne bloquez jamais sur une entrée problématique.

**Étape 4 : Validation** (`scripts/validate_html.py`, déterministe)
Vérifie que le HTML français préserve tous les éléments de l'original. Exécutée
**en lot** après les travailleurs — les agents ne valident pas individuellement.

```
python3 scripts/validate_html.py            # tout valider
python3 scripts/validate_html.py BDB17      # une seule entrée
python3 scripts/validate_html.py --summary  # totaux seulement
```

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
python3 scripts/untranslated.py 3 -n 5       # 5 entrées finissant par 3
python3 scripts/untranslated.py 7 --json     # json seulement, finissant par 7
python3 scripts/untranslated.py 4 --count    # totaux seuls, finissant par 4
```

Sans arguments, le script affiche l'aide. Les 10 chiffres (0-9) permettent à
10 travailleurs de traduire en parallèle sans chevauchement.

### Flux de traduction JSON

Un LLM lit chaque fichier de `json_output/`, traduit les champs anglais, et
écrit le résultat dans `json_output_fr/` avec le même nom de fichier.

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

Le BDB cite des mots apparentés (arabe, syriaque, éthiopien, etc.) sauvegardés
comme images GIF dans `Placeholders/` (~6 200 fichiers). En HTML :
`<placeholder1 />`, `<placeholder8 />`, etc. En texte brut :
`[placeholder8: Placeholders/8.gif]`. Le fichier `placeholders.csv` associe
chaque numéro à sa langue.

### Traitement en traduction

Copier chaque balise `<placeholder* />` telle quelle à sa position exacte — ne
pas supprimer, renuméroter ou modifier. Traduire le texte anglais environnant
(p. ex. "Arabic `<placeholder7 />`" → "arabe `<placeholder7 />`"). Les
placeholders n'apparaissent pas dans les fichiers JSON.

## Entrées squelettiques (fichiers vides)

872 entrées (~8,7 %) n'ont aucun contenu traduisible (tous champs `null`,
`senses` vide). Des fichiers de zéro octet dans `json_output_fr/` les marquent
comme traitées. Ne pas écrire de contenu dans ces fichiers.

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

Translittérations conventionnelles, conserver tels quels **y compris la
notation avec backtick** utilisée dans le HTML source (`Hiph`il`,
`Niph`al`, `Pi`el`, etc.). Ne pas simplifier en « Hiphil », « Niphal »,
etc. — reproduire exactement la graphie de l'original.

- Qal, Niph\`al, Pi\`el, Pu\`al
- Hiph\`il, Hoph\`al, Hithpa\`el
- Po\`el, Hithpo\`el, Hithpa\`al, Nithpa\`el, Pil\`el

Les étiquettes anglaises environnantes doivent être traduites :
- "Qal Perfect" -> "Qal Parfait"
- "Hiph\`il Imperfect" -> "Hiph\`il Imparfait"
- "Niph\`al Participle" -> "Niph\`al Participe"
- "Infinitive construct" -> "Infinitif construit"
- "Infinitive absolute" -> "Infinitif absolu"

## Abréviations savantes

~337 codes d'abréviation (Dl, Dr, Bev, Kau, Tg, Aq, Symm, Theod, etc.) pour
auteurs, revues et versions anciennes. Balises `<lookup>` en HTML, parfois en
ligne dans les descriptions JSON. **Ne jamais les traduire.** Préserver
exactement, y compris les notations en exposant.

## Artefacts JSON (sauts de ligne et champs `pos` débordants)

~10 % des entrées contiennent des `\n` parasites dans `pos`, `primary` ou
`description` (artefacts d'extraction). Réduire en un seul espace sauf si le
saut sépare clairement des éléments distincts.

Quelques rares entrées (~2) ont un `pos` contenant de la prose longue. Traduire
uniquement l'étiquette grammaticale au début ; déplacer le reste vers
`description` si possible, ou le conserver dans `pos` en signalant
l'irrégularité.

## Méthode de traduction obligatoire — INTERDICTION DE SCRIPTS

**Chaque entrée doit être traduite individuellement par le LLM.** Il est
interdit d'écrire des scripts de remplacement (sed, awk, `str.replace()`,
regex, etc.) pour traduire. Les seuls scripts autorisés sont ceux de `scripts/`.
Ne jamais modifier `scripts/` sauf demande explicite de l'utilisateur.

```
❌ "represented as roi de Babylone, successor, and apparent fils de Nebuchadrezzar"
✅ "présenté comme roi de Babylone, successeur et fils apparent de Nabuchodonosor"
```

Chaque champ doit être **intégralement en français** — y compris prépositions,
articles et mots de liaison. Si la sortie contient un mélange d'anglais et de
français, recommencez en traduisant la phrase entière.

## Gestion du contexte des agents

Traiter les fichiers **un par un** — que ce soit pour traduire ou pour revoir
des erreurs : lire, traiter, écrire, passer au suivant.

## Gestion des erreurs (errata)

Si vous rencontrez une entrée anormale :

1. **Produisez toujours le fichier de sortie** — même imparfait — sinon
   `untranslated.py` le signalera comme non fait.
2. **Consignez le problème** (append) dans `errata-N.txt` (N = dernier chiffre
   du BDB). Format : `BDB3370 txt_fr  description courte du problème`.
3. **Passez à l'entrée suivante.** Ne bloquez jamais.

## Vérification par LLM local (llm_verify)

`scripts/llm_verify.py` utilise un LLM local (Qwen 3.5) pour vérifier les
traductions `Entries_txt_fr/` contre `Entries_txt/`. Résultats dans
`llm_verify_txt_results.txt`. Beaucoup de signalements sont bénins
(abréviations savantes, mots français ressemblant à l'anglais comme
« raisons », termes latins), mais chaque signalement mérite une vérification
attentive. Les vrais problèmes sont surtout des petits mots anglais oubliés et
des conventions non appliquées (voir « Erreurs fréquentes »).
Le répertoire `test/` contient des données de référence pour le prompt.

### Revue des erreurs (review_errors)

Le script `scripts/review_errors.py` liste les entrées signalées par llm_verify
(ERROR, WARN, UNKNOWN) qui n'ont pas encore été revues. Une entrée est
considérée comme revue dès qu'un fichier `Entries_notes/BDBnnn.txt` existe.

```
python3 scripts/review_errors.py 0            # entrées finissant par 0
python3 scripts/review_errors.py 1 5          # entrées finissant par 1 ou 5
python3 scripts/review_errors.py 3 -n 5       # 5 entrées finissant par 3
python3 scripts/review_errors.py 4 --count    # totaux seuls, finissant par 4
python3 scripts/review_errors.py 7 --status   # avec statut et raison
```

**Flux de travail de revue :**

1. Lancer `review_errors.py` pour obtenir les prochaines entrées à revoir.
2. Pour chaque entrée, lire `Entries_txt/BDBnnn.txt` (original anglais) et
   `Entries_txt_fr/BDBnnn.txt` (traduction française).
3. Comparer avec le diagnostic de llm_verify dans `llm_verify_txt_results.txt`.
4. Écrire une note dans `Entries_notes/BDBnnn.txt` (voir format ci-dessous).
5. Si la traduction a de vrais problèmes, corriger `Entries_txt_fr/BDBnnn.txt`
   et décrire les corrections dans la note.
6. Si la traduction peut être améliorée (formulation, accents, etc.), apporter
   l'amélioration et le noter. Ne modifier que si c'est une réelle amélioration.
7. Passer à l'entrée suivante.

**Format des notes — être précis et détaillé :**

Ne jamais écrire de verdict générique qui résume sans analyser. Une note qui ne
cite pas les termes exacts signalés et n'explique pas précisément *pourquoi*
chacun est correct ou *ce qui a été corrigé* est inutile — elle empêche une
relecture future et masque de vrais problèmes.

**Si aucune correction n'est nécessaire**, la note doit quand même expliquer
concrètement pourquoi chaque terme signalé est correct. Par exemple, si le
vérificateur signale « Dl » comme anglais non traduit, la note doit dire que
c'est l'abréviation savante de Delitzsch — pas simplement « traduction
correcte ». Sans cette justification, un relecteur ne peut pas distinguer une
revue rigoureuse d'un tampon automatique.

**Obligatoire :** commencer par lire le diagnostic exact de llm_verify dans
`llm_verify_txt_results.txt` (chercher `BDBnnn.txt`), puis répondre point par
point. Toujours suivre ce format en deux parties :

- **Signalé :** citer textuellement ce que llm_verify a signalé (les termes
  exacts entre guillemets).
- **Verdict/Correction :** pour chaque terme signalé, expliquer précisément
  pourquoi c'est correct (avec la raison : abréviation savante de quel auteur,
  mot français valide dans quel sens, etc.) ou décrire ce qui a été corrigé.

Exemples :
- `Signalé : « Dl » comme anglais non traduit. Verdict : abréviation savante
  pour Delitzsch — à conserver tel quel.`
- `Signalé : « id. » et « v » non traduits. Verdict : « id. » = latin (idem),
  « v » = abréviation de verset — tous deux corrects.`
- `Signalé : « in Juda » comme anglais résiduel. Correction : « in » → « en »
  dans Entries_txt_fr.`
- `Signalé : « homer » non traduit. Verdict : translittération standard de la
  mesure hébraïque חֹמֶר, utilisée telle quelle en français savant.`

Les fichiers `Entries_notes/` servent à la fois de journal de revue et de
marqueurs de progression — `review_errors.py` les ignore automatiquement.

## Vérification de la préservation du texte hébreu (check_hebrew)

`scripts/check_hebrew.py` vérifie que chaque caractère hébreu/araméen
(U+0590–U+05FF, U+FB1D–U+FB4F) est préservé à l'identique entre `Entries_txt/`
et `Entries_txt_fr/`. Il signale aussi les fichiers français vides ou dont la
taille en caractères s'écarte de plus de 15 % de l'original anglais.

```
python3 scripts/check_hebrew.py
```

## Notes de qualité

- Viser le registre d'un ouvrage de référence contemporain en études bibliques
  francophones — pas un calque mot à mot du victorien.
- Le schéma JSON est cohérent pour les 10 022 entrées : chaque élément de
  `senses` a exactement `{number, primary, description}`.
