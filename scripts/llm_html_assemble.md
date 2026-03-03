# Réassemblage HTML — Prompt pour LLM

**Rôle :** Produire un fichier HTML **entièrement en français** en combinant le HTML anglais (structure/balises) avec le texte français traduit (contenu entre les balises).

## Règle fondamentale : visible vs invisible

- **Texte visible** (entre balises) → en français
- **Attributs** (`onclick`, `ref`, `b`, `cBegin`, etc.) → copier tel quel depuis l'original

## Traitement des balises

| Balise | Action |
|---|---|
| `<pos>`, `<primary>`, `<highlight>`, `<descrip>`, `<meta>`, `<language>`, `<gloss>` | **Traduire** le contenu |
| `<ref>` | **Traduire le texte affiché** (nom du livre) ; attributs inchangés |
| `<lookup>` | Attributs inchangés. Codes savants (Dl, Dr, Kö, Ki…) = noms propres → garder. Traduire noms de livres (`Isa`→`Es`) et prose dans `<sup>`/`<sub>` |
| `<bdbheb>`, `<bdbarc>`, `<entry>`, `<reflink>`, `<placeholder* />`, `<transliteration>`, `<checkingNeeded />`, `<wrongReferenceRemoved />` | **Préserver** tel quel |

Préserver aussi : grec ancien, sigles de manuscrits (ᵐ5, ᵑ9), noms de savants, tous les attributs. Traduire toute autre prose anglaise.

## Conventions du texte français (Entries_txt_fr)

- `^texte^` → `<sup>texte</sup>`
- `_N_` → `<sub>N</sub>`
- `[placeholderN: Placeholders/N.gif]` → `<placeholderN />`
- `&` en prose → `&amp;`
- `=== BDBnnn Hnnn ===` = en-tête structurel (ignorer)
- `---` = séparateur (`<hr>`)
- `## SPLIT N type` = marqueur de découpage (ignorer)

## Références bibliques

Abréviations françaises avec virgule chapitre/verset :
Gen→Gn, Exod→Ex, Lev→Lv, Num→Nb, Deut→Dt, Josh→Jos, Judg→Jg, Ruth→Rt, 1Sam→1 S, 2Sam→2 S, 1Kgs→1 R, 2Kgs→2 R, 1Chr→1 Ch, 2Chr→2 Ch, Ezra→Esd, Neh→Ne, Esth→Est, Job→Jb, Prov→Pr, Eccl→Qo, Song→Ct, Isa→Es, Jer→Jr, Lam→Lm, Ezek→Ez, Dan→Dn, Hos→Os, Joel→Jl, Amos→Am, Obad→Ab, Jonah→Jon, Mic→Mi, Nah→Na, Hab→Ha, Zeph→So, Hag→Ag, Zech→Za, Mal→Ml.
Format : `Gn 35,8` (virgule, pas deux-points).

## Règles critiques

1. **Sortie UNIQUEMENT HTML** — pas d'explication ni de balises markdown. Si erreur détectée, répondre `>>> ERRATA:` uniquement.
2. **Chaque balise de l'original** doit apparaître dans la sortie, imbrication identique.
3. Si pas de traduction pour un passage, garder l'anglais original plutôt qu'omettre.
4. **Aucun mot anglais** ne doit subsister (sauf `<reflink>`, `<transliteration>`, codes savants, noms de savants).
5. **Préserver les voyelles hébraïques** (nikkud) caractère par caractère.
6. **Typographie française** : espace avant ` ;` ` :` ` ?` ` !`, guillemets `« texte »`.
7. **Reproduire le texte français exactement** — pas de substitution de mots (`figuré`≠`figuratif`, `construit`≠`construct`), pas de changement de ponctuation. Le txt_fr fait autorité.
8. **Éditions savantes** : `2e éd.`, `3e éd.` depuis le français — ne pas revenir à l'anglais.
9. **Articles/prépositions français** : le français a des articles que l'anglais n'a pas. Reproduire le txt_fr mot pour mot (`bouche du roi`, `des lions`, `d'une bête`, `de la fosse` — pas de calque anglais).

## Exemples

### Exemple 1 — BDB1 (entrée simple)

HTML anglais :
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

✅ HTML français :
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

### Exemple 2 — BDB200 (nom propre avec refs)

HTML anglais :
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

✅ HTML français :
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

Note : attributs `ref="1Chr 7:16"` inchangés, texte affiché `1 Ch 7,16`.

### Exemple 3 — BDB160 (lookup avec `<sup>` traduit)

HTML anglais :
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

✅ HTML français :
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

Note : `<sup>after</sup>` → `<sup>d'après</sup>` (prose traduite dans lookup). Codes savants Di, Kö, Ki préservés. Attributs `onclick` inchangés.

## Erreurs courantes

**❌ Anglais dans `<sup>` de `<lookup>`** : `Kö<sup>I, 373, after</sup>` — `after` doit être `d'après`.

**❌ Attribut `onclick` modifié** : `onclick="bdbabb('Es')"` — l'attribut doit rester `bdbabb('Isa')`, seul le texte visible change.

**❌ Nom de livre non traduit** : `>Isa<sup>3</sup><` dans la sortie — doit être `>Es<sup>3</sup><`.

**❌ Refs non converties / ponctuation altérée** : `>Song 5:2<` doit devenir `>Ct 5,2<` ; ne pas changer `,` en ` ;` ou inversement.

**❌ Copie de l'anglais** : `<pos>proper name, masculine</pos>` — doit être `<pos>nom propre, masculin</pos>`.

**❌ Balise supprimée** : `<checkingNeeded />` ou `<wrongReferenceRemoved />` omis.

**❌ Articles français supprimés** : `bouche de roi` au lieu de `bouche du roi`, `lions` au lieu de `des lions`. Reproduire le txt_fr mot pour mot, y compris articles et contractions.

## Détection d'erreurs dans le texte français

S'il contient des erreurs évidentes, **ne pas produire de HTML** — répondre `>>> ERRATA:` suivi d'une description.

Erreurs à détecter :
- **Mots/phrases anglais non traduits** (`see`, `father`, `son of`, séquences de 3+ mots anglais courants). Exception : titres d'ouvrages.
- **Contenu sévèrement tronqué** par rapport au HTML original.
- **Refs au format anglais** (`1Chr 7:16` au lieu de `1 Ch 7,16`, deux-points au lieu de virgule).
- **Accents manquants sur majuscules** : `Esaïe`→`Ésaïe`, `Ephraïm`→`Éphraïm`, `Ezéchiel`→`Ézéchiel`, `Egypte`→`Égypte`, `Ethiopien`→`Éthiopien`.

**Pas des erreurs** : abréviations savantes, translittérations sémitiques, noms de savants, termes latins, texte hébreu/araméen/grec.

**⚠️** Ne signaler ERRATA que si le problème existe réellement dans les données fournies.

## Mode morceau (chunked)

Si un paragraphe « Mode morceau » apparaît à la fin, vous recevez une entrée partielle. Produisez le HTML complet pour ce morceau avec les balises telles qu'elles apparaissent dans l'original.

## Votre tâche

Produisez le HTML français complet ci-dessous, **sans aucun texte d'accompagnement**. Pas de markdown (` ``` `), pas de commentaire, pas de titre — votre réponse commence par `<html>` et se termine par `</html>`.

### HTML anglais original :
```
{{ORIGINAL_HTML}}
```

### Texte français traduit :
```
{{FRENCH_TXT}}
```

RAPPEL : votre réponse est UNIQUEMENT le HTML brut. Commencez directement par `<html>`.
