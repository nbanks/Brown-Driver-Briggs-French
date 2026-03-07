# Réassemblage HTML — Prompt pour LLM

**Rôle :** Produire un fichier HTML **entièrement en français** en combinant le HTML anglais (structure/balises) avec le texte français traduit (contenu entre les balises).

## Règle fondamentale : le texte français traduit fait AUTORITÉ

**Le texte français traduit est DÉFINITIF. Copiez-le MOT POUR MOT dans les balises HTML. Ne reformulez JAMAIS, ne substituez AUCUN synonyme** (`figuré`≠`figuratif`, `construit`≠`construct`, `de la fosse`≠`de fosse`). Si le texte français contient une erreur évidente (mot anglais non traduit, accent manquant, etc.), répondre `>>> ERRATA:` au lieu de produire du HTML.

## Visible vs invisible

- **Texte visible** (entre balises) → en français, copié du texte français traduit
- **Attributs** (`onclick`, `ref`, `b`, `cBegin`, etc.) → copier tel quel depuis l'original

## Traitement des balises

| Balise | Action |
|---|---|
| `<pos>`, `<primary>`, `<highlight>`, `<descrip>`, `<meta>`, `<language>`, `<gloss>` | **Copier le français** depuis le texte français traduit |
| `<ref>` | **Copier le texte affiché** (nom du livre) depuis le français ; attributs inchangés |
| `<lookup>` | Attributs inchangés. Codes savants (Dl, Dr, Kö, Ki…) = noms propres → garder. Copier noms de livres (`Isa`→`Es`) et prose dans `<sup>`/`<sub>` depuis le français |
| `<bdbheb>`, `<bdbarc>`, `<entry>`, `<reflink>`, `<placeholder* />`, `<transliteration>`, `<checkingNeeded />`, `<wrongReferenceRemoved />` | **Préserver** tel quel |

Préserver aussi : grec ancien, sigles de manuscrits (ᵐ5, ᵑ9), noms de savants, tous les attributs. Remplacer toute autre prose anglaise par le français correspondant.

## Conventions du texte français traduit

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
Les **attributs** `<ref>` gardent toujours l'anglais (`ref="1Chr 7:16"`) ; seul le **texte affiché** utilise le français (`1 Ch 7,16`).

## Règles critiques

1. **Sortie UNIQUEMENT HTML** — pas d'explication ni de balises markdown. Si erreur détectée, répondre `>>> ERRATA:` uniquement.
2. **Chaque balise de l'original** doit apparaître dans la sortie, à la même position relative que dans l'original. Ne déplacez une balise que si le texte français l'exige pour produire le bon ordre des mots visibles (voir règle 7 et exemple 4).
3. **Aucun mot anglais** ne doit subsister (sauf `<reflink>`, `<transliteration>`, codes savants, noms de savants, titres d'ouvrages).
4. **Préserver les voyelles hébraïques** (nikkud) caractère par caractère.
5. **Typographie française** : espace avant ` ;` ` :` ` ?` ` !`, guillemets `« texte »`.
6. **Éditions savantes** : `2e éd.`, `3e éd.` depuis le français — ne pas revenir à l'anglais.
7. **L'ordre des mots français prime sur l'ordre des balises anglaises.** Quand le français change l'ordre des mots autour d'un élément balisé, **déplacez la balise** pour que le texte visible corresponde au texte français traduit. Ne gardez pas l'ordre anglais des balises si cela produit un texte visible dans le mauvais ordre. Voir l'exemple 4 ci-dessous.
8. **Ne pas ajouter d'espace blanc là où l'original n'en a pas.** Ne reformatez pas le HTML — préservez les sauts de ligne et l'indentation de l'original. Si une balise fermante (`</sup>`, `</lookup>`, etc.) est collée au texte qui suit (ex. `</sup>)`), gardez-la collée. Un saut de ligne avant `)`, `,`, `;` crée une espace parasite dans le texte visible. Exemples :
   - ❌ `DHM<sup>ZMG 1875, 607</sup>\n)` → texte visible `607 )` (espace parasite)
   - ✅ `DHM<sup>ZMG 1875, 607</sup>)` → texte visible `607)` (correct)
   - ❌ `Dl<sup>Pr 170</sup>\n, sabéen` → texte visible `170 , sabéen` (espace parasite)
   - ✅ `Dl<sup>Pr 170</sup>, sabéen` → texte visible `170, sabéen` (correct)

## Exemples

### Exemple 1 — BDB1 (entrée simple)

HTML anglais original :
```
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

Texte français traduit :
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
```
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

Texte français traduit :
```
=== BDB200 H198 ===
hébreu biblique

II. אוּלָם nom propre, masculin seulement généalogie
1. 1 Ch 7,16 ; 1 Ch 7,17.
2. 1 Ch 8,39 ; 1 Ch 8,40.

---
```

HTML anglais original :
```
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
```
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

HTML anglais original :
```
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

Texte français traduit :
```
=== BDB160 H166 ===
hébreu biblique

II. [אָהַל] verbe
Hiph`il
être clair, briller, Imparfait 3 masculin singulier יַאֲהִיל (sujet lune
יָרֵחַ) Jb 25,5 (|| זַכּוּ sujet כוכבים, comparer aussi יִזְכֶּה v
Jb 25,4) (=
יָהֵל, de הלל ; par erreur textuelle ?) comparer Di
ainsi
ᵐ5
 > = I. אָהַל
Kö^I, 373, d'après^
Ki).

---
```

✅ HTML français :
```
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

### Exemple 4 — Réordonnancement de balises (l'ordre français prime)

Le français change souvent l'ordre des mots. Quand un mot contenu dans une balise (`<lookup>`, `<highlight>`, etc.) change de position dans la phrase française, **déplacez la balise** pour que le texte visible suive l'ordre français.

HTML anglais original :
```
<html>
<div class="sense">
    <sense>1.</sense> earliest poetry, <lookup onclick="bdbabb('J')">
        <reflink>J</reflink>
    </lookup> and <lookup onclick="bdbabb('E')">
        <reflink>E</reflink>
    </lookup> chiefly, <lookup onclick="bdbabb('Ephr.')">
        <reflink>Ephr</reflink>
    </lookup> document of Judges/Samuel/Kings chiefly, use <bdbheb>לֵב</bdbheb>.
</div>
</html>
```

Texte français traduit :
```
1. la poésie la plus ancienne,
J
et
E
principalement,
le document Ephr
de Juges/Samuel/Rois principalement, emploient לֵב.
```

⚠️ Piège : en anglais `Ephr` précède `document`, mais en français c'est `le document Ephr`. Si vous gardez l'ordre anglais des balises, le texte visible sera « Ephr document de » au lieu de « le document Ephr de ».

❌ FAUX (ordre anglais conservé — texte visible incorrect) :
```
    </lookup> principalement, <lookup onclick="bdbabb('Ephr.')">
        <reflink>Ephr</reflink>
    </lookup> document de Juges/Samuel/Rois
```

✅ CORRECT (balise déplacée pour suivre l'ordre français) :
```
    </lookup> principalement, le document <lookup onclick="bdbabb('Ephr.')">
        <reflink>Ephr</reflink>
    </lookup> de Juges/Samuel/Rois
```

Même principe pour `<highlight>` :

```
Anglais : <highlight>the brandishing of</highlight> ׳'s <highlight>hand</highlight>
Français : le brandissement de la main de ׳
Sortie :  <highlight>le brandissement de la</highlight> <highlight>main</highlight> de ׳
```

Le mot « main » passe avant ׳ en français ; la balise `<highlight>` suit.

## Erreurs

### Erreurs dans votre sortie HTML

- **❌ Anglais dans `<sup>` de `<lookup>`** : `Kö<sup>I, 373, after</sup>` — `after` doit être `d'après`.
- **❌ Attribut `onclick` modifié** : `onclick="bdbabb('Es')"` — l'attribut doit rester `bdbabb('Isa')`, seul le texte visible change.
- **❌ Nom de livre non converti** : `>Isa<sup>3</sup><` — doit être `>Es<sup>3</sup><`.
- **❌ Refs non converties** : `>Song 5:2<` → `>Ct 5,2<` ; ne pas altérer la ponctuation.
- **❌ Copie de l'anglais** : `<pos>proper name, masculine</pos>` — doit être `<pos>nom propre, masculin</pos>`.
- **❌ Balise supprimée** : `<checkingNeeded />` ou `<wrongReferenceRemoved />` omis.
- **❌ Balise englobante perdue** : le français dit `que l'on noue` pour `that is <highlight>bound on</highlight>` → la sortie doit être `que l'on <highlight>noue</highlight>`, PAS `que l'on noue` sans balise.
- **❌ Article français omis hors balise** : le français dit `les paroles de Dieu` pour `<highlight>words of God</highlight>` → l'article fait partie du contenu, la sortie doit être `<highlight>les paroles de Dieu</highlight>`, PAS `<highlight>paroles de Dieu</highlight>` (qui perd `les`).
- **❌ Mot dupliqué entre balises adjacentes** : le français dit `affaire, chose dont on parle` pour `<gloss>matter, affair</gloss>, <descrip>thing about which one speaks</descrip>` → ne pas traduire `affair`→`chose` dans `<gloss>` si cela duplique un mot déjà dans `<descrip>`. Sortie correcte : `<gloss>affaire</gloss>, <descrip>chose dont on parle</descrip>`.

### Erreurs dans le texte français fourni → ERRATA

Répondre `>>> ERRATA:` **uniquement** si la section « Texte français traduit » contient des erreurs de traduction évidentes. Ne pas tenter de corriger l'erreur vous-même.

Erreurs justifiant ERRATA :
- **Mots/phrases anglais non traduits** (`see`, `father`, `son of`, `in`, séquences de mots anglais courants). Exception : titres d'ouvrages.
- **Contenu sévèrement tronqué** par rapport au HTML original.
- **Refs au format anglais** (`1Chr 7:16` au lieu de `1 Ch 7,16`).
- **Accents manquants sur majuscules** : `Esaïe`→`Ésaïe`, `Ephraïm`→`Éphraïm`, `Egypte`→`Égypte`.

**Ne justifient PAS un ERRATA** : abréviations savantes, translittérations sémitiques, noms de savants, termes latins, texte hébreu/araméen/grec, balises manquantes, différences de ponctuation mineures entre le texte et le HTML.

**⚠️ Lors d'une tentative de correction** (section « Brouillon à corriger ») : les messages de correction décrivent des problèmes d'assemblage HTML à corriger (balises manquantes, texte hébreu absent, etc.). Ce sont des instructions à suivre, **PAS des raisons de signaler ERRATA**. Produisez le HTML corrigé.

**Exemple :** HTML anglais contient `<hgloss>withhold</gloss>` (balise fermante incohérente) et `<descrip>son of Kenaz, a hero in Israel</descrip>`, texte français dit `fils de Qenaz, un héros in Israël` — le mot `in` est resté en anglais. Réponse correcte :
```
>>> ERRATA: mot anglais non traduit : « in » (devrait être « en ») ; balise incohérente dans HTML anglais : <hgloss>withhold</gloss> (fermante </gloss> au lieu de </hgloss>)
```

## Mode morceau (chunked)

Si un paragraphe « Mode morceau » apparaît à la fin, vous recevez une entrée partielle. Produisez le HTML complet pour ce morceau. Toutes les règles ci-dessus s'appliquent.

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
