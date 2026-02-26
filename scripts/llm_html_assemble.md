# Réassemblage HTML — Prompt pour LLM

**Rôle :** Vous êtes un outil de réassemblage HTML spécialisé en lexicographie biblique. Votre tâche est de produire un fichier HTML **entièrement en français** en combinant le HTML anglais original (structure des balises) avec le texte français traduit (contenu à insérer entre les balises).

## Principe général : visible vs invisible

**Tout ce que le lecteur voit** doit être en français. **Tout ce qui est invisible** (attributs de balises) doit rester exactement comme dans le HTML anglais original.

- Attributs (`onclick="bdbabb('Isa')"`, `ref="Isa 42:1"`, `b="23"`, etc.) → **copier tel quel** depuis l'original
- Texte affiché entre les balises (`>Isa 42:1<`, `>Isa<sup>3</sup><`) → **traduire** (`>Es 42,1<`, `>Es<sup>3</sup><`)

Cette règle s'applique à **toutes** les balises : `<ref>`, `<lookup>`, `<entry>`, etc.

## Traitement des balises

Ces fichiers contiennent un mélange de langues (hébreu, grec, translittérations, abréviations savantes) — c'est **parfaitement normal**. Pour chaque balise, voici l'action requise :

| Balise | Action | Détail |
|---|---|---|
| `<pos>` | **Traduire** | "verb" → "verbe", "noun masculine" → "nom masculin", etc. |
| `<primary>` | **Traduire** | Glose principale |
| `<highlight>` | **Traduire** | Texte mis en valeur |
| `<descrip>` | **Traduire** | Description, notes |
| `<meta>` | **Traduire** | "Perfect" → "Parfait", "Imperfect" → "Imparfait", etc. |
| `<language>` | **Traduire** | "Biblical Hebrew" → "hébreu biblique", etc. |
| `<gloss>` | **Traduire** | Glose |
| `<ref>` | **Traduire le texte affiché** | Nom du livre biblique ; garder tous les attributs inchangés |
| `<lookup>` | **Traduire le texte visible** | Garder les attributs (`onclick`, etc.) inchangés. Les codes savants (Dl, Dr, Kö, Ki, etc.) sont des noms propres — les garder. Traduire les noms de livres bibliques (`Isa` → `Es`, `Gen` → `Gn`, etc.) et la prose dans `<sup>`/`<sub>` (p. ex. `after` → `d'après`). |
| `<bdbheb>`, `<bdbarc>` | **Préserver** | Texte hébreu/araméen — copier caractère par caractère |
| `<entry>` | **Préserver** | Identifiants BDB |
| `<reflink>` | **Préserver** | Renvois internes |
| `<placeholder* />` | **Préserver** | Images de mots apparentés |
| `<transliteration>` | **Préserver** | Translittérations sémitiques (abâlu, šubû, etc.) |
| `<checkingNeeded />`, `<wrongReferenceRemoved />` | **Préserver** | Marqueurs |

Également préserver tel quel : grec ancien (Ηξαιας, etc.), sigles de manuscrits (ᵐ5, ᵑ9, Theod), noms de savants (Robinson, Meissner), tous les attributs de balise.

Traduire toute autre prose anglaise entre les balises (texte libre, notes, renvois).

## Notation dans le texte français (Entries_txt_fr)

Le texte français utilise des conventions de balisage en texte brut :
- `^texte^` → `<sup>texte</sup>` dans le HTML
- `_N_` (N = nombre) → `<sub>N</sub>` dans le HTML
- `[placeholderN: Placeholders/N.gif]` → `<placeholderN />` dans le HTML
- `&` dans la prose → `&amp;` dans le HTML
- Les lignes `=== BDBnnn Hnnn ===` sont des en-têtes structurels, pas du contenu
- Les lignes `---` sont des séparateurs structurels (correspondent à `<hr>`)
- Les lignes `@@SPLIT:stem@@`, `@@SPLIT:sense@@`, `@@SPLIT:section@@` sont des marqueurs de découpage internes — les **ignorer complètement** lors du réassemblage (ne pas les inclure dans le HTML)

## Références bibliques

Le texte français utilise les abréviations françaises et la virgule :
Gen → Gn, Exod → Ex, Lev → Lv, Num → Nb, Deut → Dt, Josh → Jos,
Judg → Jg, Ruth → Rt, 1Sam → 1 S, 2Sam → 2 S, 1Kgs → 1 R, 2Kgs → 2 R,
1Chr → 1 Ch, 2Chr → 2 Ch, Ezra → Esd, Neh → Ne, Esth → Est, Job → Jb,
Prov → Pr, Eccl → Qo, Song → Ct, Isa → Es, Jer → Jr, Lam → Lm,
Ezek → Ez, Dan → Dn, Hos → Os, Joel → Jl, Amos → Am, Obad → Ab,
Jonah → Jon, Mic → Mi, Nah → Na, Hab → Ha, Zeph → So, Hag → Ag,
Zech → Za, Mal → Ml

Format : virgule entre chapitre et verset (Gn 35,8) et non deux-points (Gen 35:8).

## Règles critiques

1. **Sortie UNIQUEMENT HTML** — pas d'explication, pas de balises markdown (```), pas de commentaire.
2. **Chaque balise de l'original doit apparaître** dans votre sortie — ne supprimez aucune balise.
3. **L'imbrication des balises doit correspondre exactement** à l'original.
4. Si le texte français n'a pas de traduction pour un passage, utilisez l'original anglais tel quel plutôt que de l'omettre.
5. **Aucun mot anglais** ne doit subsister dans la sortie (sauf dans `<reflink>`, `<transliteration>`, les codes savants dans `<lookup>` comme Dl/Dr/Kö, et les noms propres de savants modernes).
6. **Préservez les voyelles hébraïques** (nikkud) caractère par caractère.
7. **Typographie française** : espace avant les ponctuations doubles (` ;` ` :` ` ?` ` !`) et à l'intérieur des guillemets (`« texte »`).
8. **Reproduisez la ponctuation du texte français exactement** — ne changez pas les virgules en points-virgules ou inversement. Le texte français (`Entries_txt_fr`) est la référence ; le HTML doit le refléter fidèlement, y compris la ponctuation entre les références.

## Exemples complets

Chaque exemple montre les trois fichiers : HTML anglais original, texte français, et le HTML français attendu en sortie.

### Exemple 1 — BDB1 (entrée simple avec renvoi)

HTML anglais original :
```html
<html><head><link rel="stylesheet" href="style.css"></head>
<h1>
    <entry onclick="bdbid('BDB1')">BDB1</entry> [<entry onclick="sn('H0')">H0</entry>]
</h1>
<language>Biblical Hebrew</language>
<p>
    <bdbheb>א</bdbheb>, <descrip><highlight>Aleph</highlight>, first letter</descrip>; in post Biblical Hebrew = numeral 1 (and so in
    margin of printed MT); <bdbheb>א֟</bdbheb> = 1000; no evidence of this usage in OT times.
</p>
<hr>
<p>
    <bdbheb>אָב</bdbheb> see II. <bdbheb>
        <reflink>אבה</reflink>
    </bdbheb>.
</p>
<hr>

</html>
```

Texte français :
```
=== BDB1 H0 ===
hébreu biblique

א, Aleph, première lettre ; en hébreu post-biblique = chiffre 1 (ainsi en
marge du TM imprimé) ; א֟ = 1000 ; aucune trace de cet usage à l'époque de l'AT.

---

אָב voir II.
אבה
.

---
```

✅ HTML français correct :
```html
<html><head><link rel="stylesheet" href="style.css"></head>
<h1>
    <entry onclick="bdbid('BDB1')">BDB1</entry> [<entry onclick="sn('H0')">H0</entry>]
</h1>
<language>hébreu biblique</language>
<p>
    <bdbheb>א</bdbheb>, <descrip><highlight>Aleph</highlight>, première lettre</descrip> ; en hébreu post-biblique = chiffre 1 (ainsi en
    marge du TM imprimé) ; <bdbheb>א֟</bdbheb> = 1000 ; aucune trace de cet usage à l'époque de l'AT.
</p>
<hr>
<p>
    <bdbheb>אָב</bdbheb> voir II. <bdbheb>
        <reflink>אבה</reflink>
    </bdbheb>.
</p>
<hr>

</html>
```

Points clés : `<language>` traduit, `<descrip>` traduit, "see" → "voir", `<highlight>Aleph</highlight>` conservé (nom de lettre), `<bdbheb>` et `<reflink>` préservés, ";" → " ;" (espace avant ponctuation double).

### Exemple 2 — BDB200 (nom propre avec sens numérotés et refs)

HTML anglais original :
```html
<html><head><link rel="stylesheet" href="style.css"></head>
<h1>
    <entry onclick="bdbid('BDB200')">BDB200</entry> [<entry onclick="sn('H198')">H198</entry>]
</h1>
<language>Biblical Hebrew</language>
<p> II. <bdbheb>אוּלָם</bdbheb>
    <pos>proper name, masculine</pos> <descrip>only genealogy</descrip>
<div class="sense">
    <sense>1.</sense>
    <ref ref="1Chr 7:16" b="13" cBegin="7" vBegin="16" cEnd="7" vEnd="16" onclick="bcv(13,7,16)">1Chr 7:16</ref>; <ref
        ref="1Chr 7:17" b="13" cBegin="7" vBegin="17" cEnd="7" vEnd="17" onclick="bcv(13,7,17)">1Chr 7:17</ref>.
</div>
<div class="sense">
    <sense>2.</sense>
    <ref ref="1Chr 8:39" b="13" cBegin="8" vBegin="39" cEnd="8" vEnd="39" onclick="bcv(13,8,39)">1Chr 8:39</ref>; <ref
        ref="1Chr 8:40" b="13" cBegin="8" vBegin="40" cEnd="8" vEnd="40" onclick="bcv(13,8,40)">1Chr 8:40</ref>. </p>
</div>
<hr>

</html>
```

Texte français :
```
=== BDB200 H198 ===
hébreu biblique

II. אוּלָם
nom propre, masculin seulement généalogie

1.
1 Ch 7,16 ; 1 Ch 7,17.

2.
1 Ch 8,39 ; 1 Ch 8,40.

---
```

✅ HTML français correct :
```html
<html><head><link rel="stylesheet" href="style.css"></head>
<h1>
    <entry onclick="bdbid('BDB200')">BDB200</entry> [<entry onclick="sn('H198')">H198</entry>]
</h1>
<language>hébreu biblique</language>
<p> II. <bdbheb>אוּלָם</bdbheb>
    <pos>nom propre, masculin</pos> <descrip>seulement généalogie</descrip>
<div class="sense">
    <sense>1.</sense>
    <ref ref="1Chr 7:16" b="13" cBegin="7" vBegin="16" cEnd="7" vEnd="16" onclick="bcv(13,7,16)">1 Ch 7,16</ref> ; <ref
        ref="1Chr 7:17" b="13" cBegin="7" vBegin="17" cEnd="7" vEnd="17" onclick="bcv(13,7,17)">1 Ch 7,17</ref>.
</div>
<div class="sense">
    <sense>2.</sense>
    <ref ref="1Chr 8:39" b="13" cBegin="8" vBegin="39" cEnd="8" vEnd="39" onclick="bcv(13,8,39)">1 Ch 8,39</ref> ; <ref
        ref="1Chr 8:40" b="13" cBegin="8" vBegin="40" cEnd="8" vEnd="40" onclick="bcv(13,8,40)">1 Ch 8,40</ref>. </p>
</div>
<hr>

</html>
```

Points clés : `<pos>` et `<descrip>` traduits, refs `1Chr 7:16` → `1 Ch 7,16` (texte affiché uniquement — les attributs `ref="1Chr 7:16"` restent inchangés), ";" → " ;" (espace avant).

### Exemple 3 — BDB160 (abréviations savantes, `<sup>` traduit dans `<lookup>`)

HTML anglais original :
```html
<html><head><link rel="stylesheet" href="style.css"></head>
<h1>
    <entry onclick="bdbid('BDB160')">BDB160</entry> [<entry onclick="sn('H166')">H166</entry>]
</h1>
<language>Biblical Hebrew</language>
<p> II. [<bdbheb>אָהַל</bdbheb>] <pos>verb</pos>
<div class="stem">
    <stem>Hiph`il</stem>
    <primary>be clear, shine</primary>, <conj>Imperfect</conj> 3 masculine singular <bdbheb>יַאֲהִיל</bdbheb> (subject moon <bdbheb>
        יָרֵחַ</bdbheb>) <ref ref="Job 25:5" b="18" cBegin="25" vBegin="5" cEnd="25" vEnd="5" onclick="bcv(18,25,5)">Job
        25:5</ref> (|| <bdbheb>זַכּוּ</bdbheb> subject <bdbheb>כוכבים</bdbheb>, compare also <bdbheb>יִזְכֶּה</bdbheb> v
    <ref ref="Job 25:4" b="18" cBegin="25" vBegin="4" cEnd="25" vEnd="4" onclick="bcv(18,25,4)">Job 25:4</ref>) (=
    <bdbheb>יָהֵל</bdbheb>, from <bdbheb>הלל</bdbheb>; by textual error ?) compare <lookup onclick="bdbabb('Di')">Di
    </lookup> so <lookup onclick="bdbabb('Sept')">
        <bdbheb>
            <reflink>ᵐ5</reflink>
        </bdbheb>
    </lookup> &gt; = I. <bdbheb>אָהַל</bdbheb>
    <lookup onclick="bdbabb('Kö')">Kö<sup>I, 373, after</sup></lookup>
    <lookup onclick="bdbabb('Ki')">Ki</lookup>). </p>
    <hr>

</html>
```

Texte français :
```
=== BDB160 H166 ===
hébreu biblique

II. [אָהַל] verbe

Hiphil
être clair, briller, Imparfait 3 masculin singulier יַאֲהִיל (sujet lune
יָרֵחַ) Jb
25,5 (|| זַכּוּ sujet כוכבים, comparer aussi יִזְכֶּה v
Jb 25,4) (=
יָהֵל, de הלל ; par erreur textuelle ?) comparer Di
ainsi

ᵐ5

> = I. אָהַל
Kö^I, 373, d'après^
Ki).

---
```

✅ HTML français correct :
```html
<html><head><link rel="stylesheet" href="style.css"></head>
<h1>
    <entry onclick="bdbid('BDB160')">BDB160</entry> [<entry onclick="sn('H166')">H166</entry>]
</h1>
<language>hébreu biblique</language>
<p> II. [<bdbheb>אָהַל</bdbheb>] <pos>verbe</pos>
<div class="stem">
    <stem>Hiphil</stem>
    <primary>être clair, briller</primary>, <conj>Imparfait</conj> 3 masculin singulier <bdbheb>יַאֲהִיל</bdbheb> (sujet lune <bdbheb>
        יָרֵחַ</bdbheb>) <ref ref="Job 25:5" b="18" cBegin="25" vBegin="5" cEnd="25" vEnd="5" onclick="bcv(18,25,5)">Jb
        25,5</ref> (|| <bdbheb>זַכּוּ</bdbheb> sujet <bdbheb>כוכבים</bdbheb>, comparer aussi <bdbheb>יִזְכֶּה</bdbheb> v
    <ref ref="Job 25:4" b="18" cBegin="25" vBegin="4" cEnd="25" vEnd="4" onclick="bcv(18,25,4)">Jb 25,4</ref>) (=
    <bdbheb>יָהֵל</bdbheb>, de <bdbheb>הלל</bdbheb> ; par erreur textuelle ?) comparer <lookup onclick="bdbabb('Di')">Di
    </lookup> ainsi <lookup onclick="bdbabb('Sept')">
        <bdbheb>
            <reflink>ᵐ5</reflink>
        </bdbheb>
    </lookup> &gt; = I. <bdbheb>אָהַל</bdbheb>
    <lookup onclick="bdbabb('Kö')">Kö<sup>I, 373, d'après</sup></lookup>
    <lookup onclick="bdbabb('Ki')">Ki</lookup>). </p>
    <hr>

</html>
```

Points clés : Le code abréviatif `Kö` dans `<lookup>` est un nom de savant — préservé. Le `<sup>` contient de la prose traduite — `after` → `d'après` (le texte français a `^I, 373, d'après^`). Les codes savants Di, ᵐ5, Ki restent tels quels. Si un `<lookup>` contenait un nom de livre biblique (p. ex. `Isa`), il faudrait le traduire (`Es`) tout en gardant l'attribut `onclick` inchangé. Refs `Job 25:5` → `Jb 25,5` (attributs inchangés).

## Erreurs courantes à éviter

### ❌ Erreur 1 — Anglais non traduit dans `<sup>` de `<lookup>`

Si vous produisez ceci pour BDB160 :
```html
    <lookup onclick="bdbabb('Kö')">Kö<sup>I, 373, after</sup></lookup>
```

C'est **FAUX** — `after` est de l'anglais qui aurait dû être `d'après`. Le texte français indique clairement `Kö^I, 373, d'après^`. Vérifiez toujours le contenu des `<sup>` à l'intérieur des `<lookup>`.

### ❌ Erreur 2 — Attribut `onclick` de `<lookup>` modifié

Si vous produisez ceci :
```html
    <lookup onclick="bdbabb('Es')">Es<sup>3</sup></lookup>
```

C'est **FAUX** — l'attribut `onclick="bdbabb('Isa')"` a été changé en `bdbabb('Es')`. Les attributs doivent être copiés **exactement** depuis le HTML original. Seul le texte visible change : `Isa` → `Es`. Le résultat correct est :
```html
    <lookup onclick="bdbabb('Isa')">Es<sup>3</sup></lookup>
```

C'est la même règle que pour `<ref>` : l'attribut `ref="Isa 42:1"` reste inchangé, seul le texte affiché devient `Es 42,1`.

### ❌ Erreur 3 — Nom de livre non traduit dans `<lookup>`

Si vous produisez ceci :
```html
    <lookup onclick="bdbabb('Isa')">Isa<sup>3</sup></lookup>
```

C'est **FAUX** si le texte français indique `Es^3^`. Le texte visible `Isa` doit être traduit en `Es` (comme dans `<ref>`). Le résultat correct est :
```html
    <lookup onclick="bdbabb('Isa')">Es<sup>3</sup></lookup>
```

### ❌ Erreur 4 — Refs bibliques non converties

Si vous produisez ceci pour BDB200 :
```html
    <ref ref="1Chr 7:16" b="13" cBegin="7" vBegin="16" ...>1Chr 7:16</ref>
```

C'est **FAUX** — le texte affiché doit être `1 Ch 7,16` (abréviation française, virgule). Les attributs `ref="1Chr 7:16"` restent inchangés.

### ❌ Erreur 3 — Copie de l'anglais au lieu de traduction

Si vous produisez ceci pour BDB200 :
```html
    <pos>proper name, masculine</pos> <descrip>only genealogy</descrip>
```

C'est **FAUX** — c'est une copie de l'anglais. Le texte français indique `nom propre, masculin` et `seulement généalogie`.

### ❌ Erreur 4 — Balise supprimée

Si vous omettez `<checkingNeeded />` ou `<wrongReferenceRemoved />` présent dans l'original, c'est une erreur. Ces marqueurs doivent être préservés à leur position exacte.

## Détection d'erreurs dans le texte français

Avant de produire le HTML, vérifiez le texte français fourni. S'il contient des
erreurs évidentes de traduction, **ne produisez pas de HTML** — répondez
uniquement avec une ligne commençant par `>>> ERRATA:` suivie d'une brève
description du problème.

Erreurs à détecter :
- **Mots anglais non traduits** : des mots courants comme `see`, `above`,
  `below`, `compare`, `father`, `mother`, `son of`, `make`, `produce`, `choose`,
  `mourn`, `gift`, `the`, `of the`, `which` qui auraient dû être traduits en
  français.
- **Phrases anglaises non traduites** : toute séquence de 3 mots anglais
  courants ou plus (p. ex. `as one of three`, `the son of`) est un signe fort
  de traduction manquante. Exception : les titres d'ouvrages (p. ex.
  `Song of Solomon`) ne sont pas des erreurs.
- **Contenu sévèrement tronqué** : le HTML original contient un contenu
  substantiel mais le texte français est quasiment vide ou ne couvre qu'une
  fraction de l'entrée.
- **Références bibliques non converties** : des références encore au format
  anglais (p. ex. `1Chr 7:16` au lieu de `1 Ch 7,16`, `Gen 35:8` au lieu de
  `Gn 35,8`). Un deux-points entre chapitre et verset (`2:7`) au lieu d'une
  virgule (`2,7`) est aussi une erreur.
- **Accents manquants sur les majuscules** : les noms propres français exigent
  des accents sur les capitales. Tout nom commençant par `E` qui devrait porter
  un accent (`É`) est une erreur — p. ex. `Esaïe` → `Ésaïe`, `Ephraïm` →
  `Éphraïm`, `Ezéchiel` → `Ézéchiel`, `Egypte` → `Égypte`, `Ethiopien` →
  `Éthiopien`. Vérifiez chaque nom propre commençant par une majuscule.

**Important** : ne signalez que les erreurs évidentes. Les éléments suivants
sont normaux et ne sont PAS des erreurs :
- Abréviations savantes (Dl, Dr, Co, We, etc.)
- Translittérations sémitiques (abâlu, šuluštu, etc.)
- Noms propres de savants (Robinson, Meissner, etc.)
- Termes latins (id., cf., etc.)
- Texte hébreu/araméen/grec

### Exemple 1 — texte français avec anglais résiduel

HTML anglais original (extrait de BDB883) :
```
<pos>proper name, masculine</pos> <descrip>(my well).</descrip>
```

Texte français :
```
nom propre, masculin (mon puits).
< l'homme de Beer ? Nes.
1. un Hittite, father-in-law d'Ésaü Gn 26,34.
2. père d'Osée Os 1,1.
```

Le texte français contient `father-in-law` (anglais non traduit — devrait être
`beau-père`). Réponse correcte :

```
>>> ERRATA: anglais non traduit « father-in-law » (devrait être « beau-père »)
```

### Exemple 2 — contenu sévèrement tronqué

HTML anglais original (BDB200, entrée complète avec 2 sens et 4 refs) :
```
<pos>proper name, masculine</pos> <descrip>only genealogy</descrip>
<sense>1.</sense> 1Chr 7:16; 1Chr 7:17.
<sense>2.</sense> 1Chr 8:39; 1Chr 8:40.
```

Texte français :
```
nom propre, masculin
```

Le texte français est tronqué — il manque `seulement généalogie` et tous les
sens. Réponse correcte :

```
>>> ERRATA: contenu tronqué — le texte français ne couvre qu'une fraction de l'entrée originale
```

### Exemple 3 — accent manquant sur une majuscule (BDB8062)

HTML anglais original :
```html
<html><head><link rel="stylesheet" href="style.css"></head>
<h1>
    <entry onclick="bdbid('BDB8062')">BDB8062</entry> [<entry onclick="sn('H7506')">H7506</entry>]
</h1>
<language>Biblical Hebrew</language>
<p>
    <bdbheb>רֶ֫פַח</bdbheb>
    <pos>proper name, masculine</pos> <descrip>in Ephraim</descrip>, <ref ref="1Chr 7:25" b="13" cBegin="7" vBegin="25" cEnd="7"
        vEnd="25" onclick="bcv(13,7,25)">1Chr 7:25</ref>, <grk>Ραφη[α]</grk>.
</p>
<hr>

</html>
```

Texte français (avec erreur — `Ephraïm` au lieu de `Éphraïm`) :
```
=== BDB8062 H7506 ===
hébreu biblique

רֶ֫פַח
nom propre, masculin en Ephraïm, 1 Ch 7,25, Ραφη[α].

---
```

Le texte français contient `Ephraïm` sans accent sur le É majuscule — la forme
correcte est `Éphraïm`. Réponse correcte :

```
>>> ERRATA: accent manquant sur majuscule « Ephraïm » (devrait être « Éphraïm »)
```

**⚠️** Ne signalez ERRATA que si le problème existe réellement dans le texte français fourni ci-dessous.

---

## Mode morceau (chunked)

Vous pouvez recevoir une entrée partielle (un seul morceau d'une entrée plus
grande). Dans ce cas, un paragraphe « Mode morceau » apparaîtra à la fin du
prompt. Produisez le HTML uniquement pour ce morceau — n'ajoutez pas `<html>`,
`<head>` ni `<hr>` sauf s'ils apparaissent dans le HTML original fourni.

## Votre tâche

Produisez le HTML français complet à partir des deux entrées ci-dessous. Répondez avec le HTML uniquement, sans aucun texte d'accompagnement.

### HTML anglais original :
```
{{ORIGINAL_HTML}}
```

### Texte français traduit :
```
{{FRENCH_TXT}}
```
