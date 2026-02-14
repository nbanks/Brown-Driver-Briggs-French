# Brown-Driver-Briggs Enhanced -- Projet de lexique français

## Présentation du projet

Le Brown-Driver-Briggs Hebrew and English Lexicon (BDB) est le dictionnaire de
référence pour l'hébreu biblique et l'araméen. Publié initialement en 1906, ses
définitions anglaises emploient une prose victorienne archaïque, parfois guindée.

Ce projet maintient une extraction JSON structurée de chaque entrée BDB
(`json_output/`, ~10 022 fichiers) ainsi que les entrées HTML originales
(`Entries/`). L'objectif de la **conversion en lexique français** est de
produire un ensemble parallèle de fichiers JSON (`json_output.fr/`) et HTML
(`Entries.fr/`) où tout le contenu en anglais est rendu en français moderne et
clair, tout en préservant intégralement chaque mot-vedette hébreu ou araméen,
chaque lemme et chaque notation morphologique.

## Arborescence

```
Brown-Driver-Briggs-Enhanced/
    Entries/            # Entrées HTML originales du BDB (lecture seule)
    Entries.fr/         # Entrées HTML en français
    json_output/        # JSON anglais, un fichier par entrée BDB (source)
    json_output.fr/     # JSON français, un fichier par entrée BDB (cible)
    Placeholders/       # ~6 200 images GIF de scripts de langues apparentées
    bdbToStrongsMapping.csv
    placeholders.csv
    untranslated.py     # script utilitaire : liste les fichiers non traduits
    CLAUDE.md -> /home/ai/.claude/CLAUDE.md   # conventions de codage
    AGENTS.md           # ce fichier -- instructions spécifiques au projet
```

## Accents et UTF-8

**Toute sortie en français DOIT utiliser les accents et diacritiques corrects.**
Il s'agit d'un ouvrage de référence savant ; le français sans accents est
inacceptable. Exemples :

- « usé » et non « use », « blé » et non « ble », « être » et non « etre »
- « féminin » et non « feminin », « généalogie » et non « genealogie »
- « Néhémie » et non « Nehemie », « Deutéronome » et non « Deuteronome »
- « c.-à-d. » et non « c.-a-d. », « là » et non « la » (quand c'est l'adverbe)
- « hébreu » et non « hebreu », « araméen » et non « arameen »
- « phénicien » et non « phenicien », « éthiopien » et non « ethiopien »
- « fraîcheur » et non « fraicheur », « première » et non « premiere »

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

### Exemples JSON (json_output/ -> json_output.fr/)

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

### Exemples HTML (Entries/ -> Entries.fr/, balises retirées)

Ces exemples montrent le contenu textuel lisible résultant de la traduction du
HTML. Dans les fichiers réels, les balises XML (`<pos>`, `<primary>`,
`<bdbheb>`, `<ref>`, etc.) doivent être préservées -- seul le texte anglais
entre les balises est traduit.

**BDB1** -- א Aleph
```
English: Aleph, first letter; in post-biblical Hebrew = numeral 1
French:  Aleph, première lettre ; en hébreu post-biblique = chiffre 1
```

**BDB50** -- אָבַל mourn
```
English: verb  mourn  (Assyrian [abâlu])
         Qal Perfect אָבַל Isa 24:7 ...
         mourn, lament (poet. & elevated style); absolute, human subject
         Joel 1:9; Amos 8:8 ...
French:  verbe  être en deuil  (assyrien [abâlu])
         Qal Accompli אָבַל Es 24,7 ...
         être en deuil, se lamenter (poétique & style élevé) ; absolu,
         sujet humain Jl 1,9 ; Am 8,8 ...
```

**BDB200** -- אוּלָם nom propre
```
English: proper name, masculine  only genealogy  1Chr 7:16; 1Chr 7:17
French:  nom propre, masculin  seulement généalogie  1 Ch 7,16 ; 1 Ch 7,17
```

**BDB50 (section Hithpael)** -- deuil pour les morts
```
English: mourn (especially prose) especially for the dead,
         followed by על Gen 37:34; 2Sam 13:37; ... compare also
         Isa 66:10 (concerning Jerusalem)
French:  être en deuil (surtout prose) surtout pour les morts,
         suivi de על Gn 37,34 ; 2 S 13,37 ; ... comparer aussi
         Es 66,10 (concernant Jérusalem)
```

**BDB50 (section Hiphil)** -- causatif du deuil
```
English: cause to mourn; Ezek 31:15 ... caused the deep to mourn over
French:  faire porter le deuil ; Ez 31,15 ... a fait porter le deuil
         à l'abîme sur
```

**BDB1 (renvoi)** -- schéma typique de renvoi
```
English: אָב see II. אבה
French:  אָב voir II. אבה
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

### Script utilitaire : `untranslated.py`

Affiche les fichiers qui restent à traduire. Il compare `json_output/` avec
`json_output.fr/` et `Entries/` avec `Entries.fr/`, en listant les fichiers
manquants dans l'ordre numérique BDB. Affiche par défaut jusqu'à 20 entrées
avec des chemins relatifs.

Le script requiert un ou plusieurs **arguments numériques** (0-9) qui filtrent
les entrées par le dernier chiffre du numéro BDB. Cela permet à 10 travailleurs
de traduire le corpus en parallèle sans chevauchement -- chacun reçoit une
tranche disjointe.

```
python3 untranslated.py 0            # entrées finissant par 0
python3 untranslated.py 1 5          # entrées finissant par 1 ou 5
python3 untranslated.py 0 1 2 3 4 5 6 7 8 9   # tout
python3 untranslated.py 3 -n 5       # afficher 5, finissant par 3
python3 untranslated.py 7 --json     # json seulement, finissant par 7
python3 untranslated.py 2 --html     # html seulement, finissant par 2
python3 untranslated.py 9 --count    # totaux seuls, finissant par 9
```

Sans arguments, le script affiche l'aide. Code de sortie 0 quand la tranche
est entièrement traduite, 1 quand des fichiers restent, 2 en cas d'arguments
invalides.

Exemple de partitionnement (10 travailleurs) :
- Travailleur A : `untranslated.py 0`  (~1 002 entrées)
- Travailleur B : `untranslated.py 1`  (~1 002 entrées)
- ...
- Travailleur J : `untranslated.py 9`  (~1 002 entrées)

### Flux de traduction JSON

La conversion se fait par lots. Un script lit chaque fichier de `json_output/`,
traduit les champs anglais pertinents (y compris les noms de livres bibliques
dans `description` et `senses[].description`), et écrit le résultat dans
`json_output.fr/` avec le même nom de fichier. Le script doit être idempotent :
une réexécution écrase les fichiers français existants sans duplication.

### Flux de traduction HTML

Les entrées HTML dans `Entries/` contiennent un mélange de balises XML
personnalisées, d'écriture hébraïque/araméenne, de prose anglaise et de
balisage structurel. Leur traduction nécessite une approche en plusieurs
étapes :

1. **Extraire le texte traduisible.** Analyser le HTML et extraire uniquement
   le contenu textuel en anglais, en ignorant :
   - Les balises `<bdbheb>` et `<bdbarc>` (hébreu/araméen -- préserver tel quel)
   - Les balises `<entry>` (identifiants BDB et numéros Strong)
   - Les attributs des balises `<ref>` (garder les attributs ; traduire le texte
     affiché)
   - Les abréviations savantes `<lookup>`
   - Le contenu `<transliteration>`
   Écrire l'anglais extrait dans un fichier `.txt` de travail (un segment par
   ligne, étiqueté avec sa position source pour pouvoir le réinsérer).

2. **Traduire le texte.** Convertir l'anglais extrait en français moderne, en
   appliquant les mêmes règles que pour le JSON : traduire les gloses, les
   descriptions, les étiquettes grammaticales et les noms de livres bibliques.
   Laisser inchangées les chaînes hébraïques/araméennes qui apparaissent en
   ligne dans le texte.

3. **Réassembler le HTML.** Réinsérer le texte français dans la structure HTML
   originale, en préservant toutes les balises, attributs et contenus
   hébreux/araméens à leur position d'origine. Écrire le résultat dans
   `Entries.fr/` avec le même nom de fichier. Le texte affiché des `<ref>`
   (p. ex. "Dan 7:5") doit apparaître avec l'abréviation française du livre
   (p. ex. "Dn 7,5") tandis que les attributs `ref=` restent inchangés.

Balises et leur traitement lors de l'extraction :
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
`json_output.fr/` afin que `untranslated.py` les ignore. Pour les retrouver :

```bash
find json_output.fr/ -empty -name '*.json'   # lister les placeholders vides
find json_output.fr/ -empty | wc -l          # les compter (872 attendus)
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
- "Qal Perfect" -> "Qal accompli"
- "Hiph'il Imperfect" -> "Hiphil inaccompli"
- "Niph'al Participle" -> "Niphal participe"
- "Infinitive construct" -> "infinitif construit"
- "Infinitive absolute" -> "infinitif absolu"

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

## Notes de qualité

- Le texte original du BDB est en anglais de l'époque victorienne. Le français
  doit être moderne, accessible et précis -- pas un calque mot à mot. Viser le
  registre d'un ouvrage de référence contemporain en études bibliques
  francophones.
- **Toujours utiliser les accents et diacritiques français corrects.** Voir la
  section « Accents et UTF-8 » ci-dessus et le tableau des mots courants. Le
  français sans accents (p. ex. « etre », « feminin », « Nehemie ») est un
  défaut de qualité.
- Le style français de référence biblique utilise une virgule entre chapitre et
  verset (p. ex. « Dn 7,5 » et non « Dn 7:5 »), conformément à la convention
  de la Bible de Jérusalem et de la TOB.
- Le schéma JSON est cohérent pour les 10 022 entrées : chaque élément de
  `senses` a exactement `{number, primary, description}`. Il n'existe pas de
  structures imbriquées ou variantes.
