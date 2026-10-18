from submission import pairs
def test_pairs():
    actual = pairs()
    assert [key for key, _ in actual] == ["a", "b"]
    assert [value for _, value in actual] == [2, 3]
