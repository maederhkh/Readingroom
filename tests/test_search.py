"""Keyword search: which parts of the laws match the words, and in what order.

The scoring rules are shown on tiny made-up articles, where each rule is easy to see.
tests/test_real_search.py checks the same search on the real laws.
"""
from readingroom.search import KeywordIndex, Passage, tokenize


def passage(number, text, doc_id="law", kind="article"):
    return Passage(doc_id=doc_id, kind=kind, number=number, title=f"Title {number}",
                   page_start=1, page_end=1, text=text)


def numbers(hits):
    return [hit.passage.number for hit in hits]


def test_words_are_lowercased_and_split_on_anything_not_a_letter_or_digit():
    assert tokenize("Article 5(1)(d): ‘accuracy’, Regulation (EU) 2016/679") == [
        "article", "5", "1", "d", "accuracy", "regulation", "eu", "2016", "679"]


def test_only_articles_containing_a_query_word_are_returned():
    index = KeywordIndex([passage(1, "personal data shall be accurate"),
                          passage(2, "the supervisory authority")])
    assert numbers(index.search("accurate")) == [1]


def test_a_rare_word_counts_more_than_a_common_one():
    # Every article is two words long and matches exactly one query word, so rarity is
    # the only thing that can separate them. "data" is in three articles, "accuracy" in
    # one: Article 4 wins. (The first version of this test let the winner match both
    # words, and still passed with rarity switched off - so it tested nothing.)
    index = KeywordIndex([passage(1, "data x"),
                          passage(2, "data y"),
                          passage(3, "data z"),
                          passage(4, "accuracy x")])
    assert numbers(index.search("data accuracy"))[0] == 4


def test_repeating_a_word_helps():
    index = KeywordIndex([passage(1, "consent is given"),
                          passage(2, "consent consent consent is given"),
                          passage(3, "nothing relevant here")])
    assert numbers(index.search("consent")) == [2, 1]


def test_repeating_a_word_helps_less_each_time():
    # Three articles of equal length (21 words) mentioning "consent" 1, 2 and 20 times.
    index = KeywordIndex([passage(1, "consent " * 1 + "x " * 20),
                          passage(2, "consent " * 2 + "x " * 19),
                          passage(20, "consent " * 20 + "x " * 1),
                          passage(99, "unrelated")])
    score = {hit.passage.number: hit.score for hit in index.search("consent")}
    second_mention = score[2] - score[1]
    each_later_mention = (score[20] - score[2]) / 18
    assert second_mention > each_later_mention
    assert score[20] < 3 * score[1]  # twenty mentions are worth far less than twenty times one


def test_a_long_article_does_not_win_just_by_being_long():
    short = "consent withdrawal"
    long = "consent " + " ".join(f"word{i}" for i in range(300))
    index = KeywordIndex([passage(1, long), passage(2, short), passage(3, "other")])
    assert numbers(index.search("consent")) == [2, 1]


def test_a_quoted_phrase_must_appear_as_those_words_in_that_order():
    index = KeywordIndex([passage(1, "kept up to date"),
                          passage(2, "up to the date it was kept"),
                          passage(3, "irrelevant")])
    assert numbers(index.search('"kept up to date"')) == [1]


def test_a_phrase_matches_across_a_line_break():
    # The clean text keeps the PDF's line breaks, often in mid-sentence.
    index = KeywordIndex([passage(1, "shall be accurate and, where necessary, kept up\nto date"),
                          passage(2, "other")])
    assert numbers(index.search('"kept up to date"')) == [1]


def test_words_outside_quotes_still_count_alongside_a_phrase():
    # Same length, so only the extra word "erased" can separate them.
    index = KeywordIndex([passage(1, "kept up to date and stored without delay"),
                          passage(2, "kept up to date and erased without delay"),
                          passage(3, "erased")])            # has the word but not the phrase
    assert numbers(index.search('"kept up to date" erased')) == [2, 1]


def test_nothing_matching_returns_nothing():
    index = KeywordIndex([passage(1, "personal data")])
    assert index.search("zebra") == []
    assert index.search("") == []


def test_search_can_be_limited_to_some_laws():
    index = KeywordIndex([passage(1, "consent", doc_id="gdpr"),
                          passage(1, "consent", doc_id="dsa")])
    assert [h.passage.doc_id for h in index.search("consent", laws=["dsa"])] == ["dsa"]


def test_limit_caps_the_number_of_results():
    index = KeywordIndex([passage(n, "consent") for n in range(1, 11)])
    assert len(index.search("consent", limit=3)) == 3


def test_the_snippet_shows_the_words_where_they_appear():
    text = "Article 5\nPrinciples\n" + "filler words here. " * 40 + "kept up\nto date" + " more filler." * 40
    index = KeywordIndex([passage(5, text), passage(6, "other")])
    [hit] = index.search('"kept up to date"')
    assert "kept up to date" in hit.snippet          # line break shown as a space
    assert hit.snippet.startswith("…") and hit.snippet.endswith("…")
    assert len(hit.snippet) < 400


def test_the_bookmark_names_the_law_the_kind_and_the_number():
    assert passage(5, "x", doc_id="gdpr").bookmark == "gdpr/article-5"
    assert passage(71, "x", doc_id="gdpr", kind="recital").bookmark == "gdpr/recital-71"
    assert passage("III", "x", doc_id="eu-ai-act", kind="annex").bookmark == "eu-ai-act/annex-III"


def test_the_label_is_how_a_lawyer_would_cite_it():
    assert passage(5, "x").label == "Article 5"
    assert passage(71, "x", kind="recital").label == "Recital 71"
    assert passage("III", "x", kind="annex").label == "Annex III"


def test_search_can_be_limited_to_some_kinds():
    index = KeywordIndex([passage(22, "automated decision", kind="article"),
                          passage(71, "automated decision", kind="recital"),
                          passage("III", "automated decision", kind="annex")])
    assert [h.passage.kind for h in index.search("automated", kinds=["recital"])] == ["recital"]
    assert {h.passage.kind for h in index.search("automated", kinds=["article", "annex"])} == {"article", "annex"}


def test_grouped_search_puts_articles_first_even_when_a_recital_scores_higher():
    # The real problem: recitals repeat the key words in plain sentences and outscore
    # the binding article. "prohibited AI practices" returned five recitals and no articles.
    index = KeywordIndex([passage(5, "the following practices shall be prohibited " + "x " * 40),
                          passage(28, "prohibited practices prohibited practices", kind="recital"),
                          passage("III", "prohibited practices list", kind="annex"),
                          passage(9, "unrelated")])
    assert index.search("prohibited practices")[0].passage.kind == "recital"     # the problem
    assert [h.passage.bookmark for h in index.search_grouped("prohibited practices")] == [
        "law/article-5", "law/recital-28", "law/annex-III"]


def test_grouped_search_takes_the_best_few_of_each_kind():
    index = KeywordIndex([passage(n, "consent") for n in range(1, 9)]
                         + [passage(n, "consent", kind="recital") for n in range(1, 9)]
                         + [passage(n, "consent", kind="annex") for n in ("I", "II", "III", "IV")])
    kinds = [h.passage.kind for h in index.search_grouped("consent", limit=4)]
    assert kinds == ["article"] * 4 + ["recital"] * 3 + ["annex"] * 2


def test_grouped_search_respects_the_law_filter():
    index = KeywordIndex([passage(1, "consent", doc_id="gdpr"), passage(1, "consent", doc_id="dsa", kind="recital")])
    assert [h.passage.doc_id for h in index.search_grouped("consent", laws=["gdpr"])] == ["gdpr"]
