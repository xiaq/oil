---
default_highlighter: oil-sh
---

Known Differences Between OSH and Other Shells
==============================================

This document is for **sophisticated shell users**.

You're unlikely to encounter these incompatibilities in everyday shell usage.
If you do, there's almost always a **simple workaround**, like adding a space
or a backslash.

OSH is meant to run all POSIX shell programs, and most bash programs.

<!-- cmark.py expands this -->
<div id="toc">
</div>

<!-- 
TODO:

- `` as comments in sandstorm
  # This relates to comments being EOL or not

- Document when declare / local / readonly/ export are KEYWORDS, and when they
  are BUILTINS.

-->

## Numbers and Arithmetic

### printf '%d' and other numeric formats require a valid integer

In other shells, `printf %d invalid_integer` prints `0` and a warning.  OSH
gives you a runtime error.

### Code Parsed from Data Can't Have Command Subs unless `shopt -s eval_unsafe_arith`

In shell, array locations are often dynamically parsed, and the index can have
command subs, which execute arbitrary code.

For example, if you have `code='a[$(echo 42 | tee PWNED)]'`, shells will parse
this data and execute it in many sitautions:

    echo $(( code ))  # dynamic parsing and evaluation in bash, mksh, zsh

    unset $code

    printf -v $code hi

    echo ${!code}

OSH disallows this by default.  If you want this behavior, you can turn on
`shopt -s eval_unsafe_arith`.

Related: [A 30-year-old security problem](https://www.oilshell.org/blog/2019/01/18.html#a-story-about-a-30-year-old-security-problem)

## Parsing Differences

This section describes differences related to [static
parsing](http://www.oilshell.org/blog/2016/10/22.html).  OSH avoids the
dynamic parsing of most shells.

(Note: This section should encompass all the failures from the [wild
tests](http://oilshell.org/cross-ref.html?tag=wild-test#wild-test) and [spec
tests](http://oilshell.org/cross-ref.html?tag=spec-test#spec-test).

### Strings vs. Bare words in array indices

Strings should be quoted inside array indices:

No:

    "${SETUP_STATE[$err.cmd]}"

Yes:

    "${SETUP_STATE["$err.cmd"]}"

When unquoted, the period causes an ambiguity with respect to regular arrays
vs. associative arrays.  See [Parsing Bash is
Undecidable](http://www.oilshell.org/blog/2016/10/20.html).


### Subshell in command sub

You can have a subshell in a command sub, but it usually doesn't make sense.

In OSH you need a space after `$(`.  The characters `$((` always start an
arith sub.

No:

    $((cd / && ls))

Yes:

    $( (cd / && ls) )   # Valid but usually doesn't make sense.
    $({ cd / && ls; })  # Use {} for grouping, not ().  Note trailing ;
    $(cd / && ls)       # Even better


### Extended glob vs. Negation of boolean expression

The OSH parser distinguishes these two constructs with a space:

- `[[ !(a == a) ]]` is an extended glob.
- `[[ ! (a == a) ]]` is the negation of an equality test.

In bash, the parsing of such expressions depends on `shopt -s extglob`.  In
OSH, `shopt -s extglob` is accepted, but doesn't affect parsing.

### Here doc terminators must be on their own line

Lines like `EOF]` or `EOF)` don't end here docs.  The delimiter must be on its
own line.

No:

    a=$(cat <<EOF
    abc
    EOF)

    a=$(cat <<EOF
    abc
    EOF  # this is not a comment; it makes the EOF delimiter invalid
    )

Yes:

    a=$(cat <<EOF
    abc
    EOF
    )  # this is actually a comment


### Spaces aren't allowed in LHS indices

Bash allows:

    a[1 + 2 * 3]=value

OSH only allows:

    a[1+2*3]=value

because it parses with limited lookahead.  The first line would result in the
execution of a command named `a[1`.

### break / continue / return are keywords, not builtins

This means that they aren't "dynamic":

    b=break
    while true; do
      $b  # doesn't break in OSH
    done

Static control flow will allow static analysis of shell scripts.

(Test cases are in [spec/loop][]).

### Oil Has More Builtins, Which Shadow External Commands

For example, `push` is a builtin in Oil, but not in `bash`.  Use `env push` or
`/path/to/push` if you want to run an external command.

(Note that a user-defined function `push` take priority over the builtin
`push`.

### Oil Has More Keywords, Which Shadow Builtins, Functions, and Commands

In contrast with builtins, **keywords** affect shell parsing.

For example, `func` is a keyword in Oil, but not in `bash`.  To run a command
named `func`, use `command func arg1`.

Note that all shells have extensions that cause this issue.  For example, `[[`
is a keyword in `bash` but not in POSIX shell.

## More Parsing Differences

These differences occur in subsequent stages of parsing, or in runtime parsing.

### Brace expansion is all or nothing

No:

    {a,b}{        # what does the second { mean?
    {a,b}{1...3}  # 3 dots instead of 2

Yes:

    {a,b}\{
    {a,b}\{1...3\}

bash will do a **partial expansion** in the former cases, giving you `a{ b{`
and `a{1...3} b{1...3}`.

OSH considers them syntax errors and aborts all brace expansion, giving you
the same thing back: `{a,b}{` and `{a,b}{1...3}`.


### Tilde expansion and Brace expansion don't interact

In bash, `{~bob,~jane}/src` will expand the home dirs of both people.  OSH
doesn't do this because it separates parsing and evaluation.  By the time tilde
expansion happens, we haven't *evaluated* the brace expansion.  We've only
*parsed* it.

(mksh agrees with OSH, but zsh agrees with bash.)

### Brackets should be escaped within character classes

Don't use ambiguous syntax for a character class consisting of a single bracket
character.

No:

    echo [[]
    echo []]

Yes:

    echo [\[]
    echo [\]]


The ambiguous syntax is allowed when we pass globs through to `libc`, but it's
good practice to be explicit.

### Double quotes within backticks

In rare cases, OSH processes backslashes within backticks differently than
other shells.  However there are **two workarounds** that are compatible with
every shell.

No:

    `echo \"`     # is this a literal quote, or does it start a string?

Yes:

    $(echo \")    # $() can always be used instead of ``.
                  # There's no downside to the more modern construct.
    `echo \\"`    # also valid, but $() is more readable


Notes:

- This is tested in [spec/command-sub][].  (Case #25 fails for OSH, and all
  shells start to disagree on case #26.)
- The reason for the disagreement is that OSH doesn't have special cases for a
  particular number of backslashes.  The rules are consistent for any level of
  quoting, although incompatible in this edge case.

## Differences at Runtime

### Alias Expansion

Almost all "real" aliases should work in OSH.  But these don't work:

    alias left='{'
    left echo hi; }

(cases #33-#34 in [spec/alias][])

or

    alias a=
    a (( var = 0 ))

Details on the OSH parsing model:

1. Your code is statically parsed into an abstract syntax tree, which contains
   many types of nodes.
2. `SimpleCommand` are the only ones that are further alias-expanded.

For example, these result in `SimpleCommand` nodes:

- `ls -l` 
- `read -n 1` (normally a builtin)
- `myfunc foo`

These don't:

- `x=42`
- `declare -r x=42`
- `break`, `continue`, `return`, `exit` &mdash; as explained above, these are
  keywords and not builtins.
- `{ echo one; echo two; }`
- `for`, `while`, `case`, functions, etc.

### Array Indices Aren't Dynamically Parsed

### Array References Must be Explicit

In bash, `$array` is equivalent to `${array[0]}`, which is very confusing
(especially when combined with `set -o nounset`).

No:

    array=(1 2 3)
    echo $array         # Runtime error in OSH

Yes:

    echo ${array[0]}    # explicitly choose the first element
    echo "${array[@]}"  # explicitly choose the whole array

NOTE: Setting `shopt -s strict_array` further reduces the confusion between
strings and arrays.  See the [options doc](options.html) for details.

### Arrays aren't split inside ${}

Most shells split the entries of arrays like `"$@"` and `"${a[@]}"` here:

    echo ${undef:-"$@"}

In OSH, omit the quotes if you want splitting:

    echo ${undef:-$@}

I think OSH is more consistent, but it disagrees with other shells.

### Values Are Tagged with Types, Not Locations (`declare -i -a -A`)

Even though there's a large common subset, OSH and bash have a different model
for typed data.

- In OSH, **values** are tagged with types, which is how Python and JavaScript
  work.
- In bash, **cells** (locations for values) are tagged with types.  Everything
  is a string, but in certain contexts, strings are treated as integers or as
  structured data.

In particular,

- The `-i` flag is a no-op in OSH.  See [Shell Idioms > Remove Dynamic
  Parsing](shell-idioms.html#remove-dynamic-parsing) for alternatives to `-i`.
- The `-a` and `-A` flags behave differently.  They pertain to the value, not
  the location.

For example, these two statements are different in bash, but the same in OSH:

    declare -A assoc     # unset cell that will LATER be an assoc array
    declare -A assoc=()  # empty associative array

In bash, you can tell the difference with `set -u`, but there's no difference
in OSH.

### Indexed and Associative Arrays are Distinct

Here is how you can create arrays in OSH, in a bash-compatible way:

    local indexed=(foo bar)
    local -a indexed=(foo bar)            # -a is redundant
    echo ${indexed[1]}                    # bar

    local assoc=(['one']=1 ['two']=2)
    local -A assoc=(['one']=1 ['two']=2)  # -A is redundant
    echo ${assoc['one']}                  # 1

In bash, the distinction between the two is blurry, with cases like this:

    local -A x=(foo bar)                  # -A disagrees with literal
    local -a y=(['one']=1 ['two']=2)      # -a disagrees with literal

These are disallowed in OSH.

Notes:

- The [pp]($help:pp) builtin is useful for gaining an understanding of the
data model.
- See the [Quirks](quirks.html) doc for details on how Oil uses this cleaner
  model while staying compatible with bash.

### Args to Assignment Builtins Aren't Split or Globbed

The assignment builtins are `export`, `readonly`, `local`, and
`declare`/`typeset`.

In bash, you can do unusual things with them:

    vars='a=b x=y'
    touch foo=bar.py spam=eggs.py

    declare $vars *.py       # assigns at least 4 variables
    echo $a       # b
    echo $x       # y
    echo $foo     # bar.py
    echo $spam    # eggs.py

In contrast, OSH disables splitting and globbing within assignment builtins.
This is more like the behavior of zsh.

On a related note, assignment builtins are both statically and dynamically
parsed:

- Statically: to avoid splitting `declare x=$y` when `$y` contains spaces.
- Dynamically: to handle expressions like `declare $1` where `$1` is `a=b`

### Extended globs are more static like `mksh`, and have other differences

That is, in OSH and mksh, something like `echo *.@(cc|h)` is an extended glob.
But `echo $x`, where `$x` contains the pattern, is not.

For more details and differences, see the [Extended Glob
section](word-language.html#extended-glob) of the Word Language doc.

### Completion

The OSH completion API is mostly compatible with the bash completion API,
except that it moves the **responsibility for quoting** out of plugins and onto
the shell itself.  Plugins should return candidates as `argv` entries, not
shell words.

See the [completion doc](completion.html) for details.

## Interactive Features

### History Substitution Language

The rules for history substitution like `!echo` are simpler.  There are no
special cases to avoid clashes with `${!indirect}` and so forth.

TODO: Link to the history lexer.

## Links

- [OSH Spec Tests](../test/spec.wwz/survey/osh.html) run shell snippets with OSH and other
  shells to compare their behavior.

External:

- This list may seem long, but compare the list of differences in [Bash POSIX
  Mode](https://www.gnu.org/software/bash/manual/html_node/Bash-POSIX-Mode.html).
  That page tells you what `set -o posix` does in bash.


[spec/command-sub]: ../test/spec.wwz/command-sub.html
[spec/loop]: ../test/spec.wwz/loop.html
[spec/alias]: ../test/spec.wwz/alias.html


