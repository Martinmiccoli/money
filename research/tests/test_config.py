import pytest

from money_research.config import ConfigError, isin_is_valid, load_universe


def test_repo_universe_is_valid():
    inst = load_universe()
    ids = [i.id for i in inst]
    assert len(ids) == len(set(ids))
    assert "all_world" in ids  # benchmark obbligatorio
    bench = next(i for i in inst if i.id == "all_world")
    assert "benchmark" in bench.sleeves and bench.isin


@pytest.mark.parametrize(
    "isin", ["IE00BK5BQT80", "IE00B4L5Y983", "IE00B5BMR087", "IE00BKM4GZ66", "IE00B4ND3602", "US0378331005"]
)
def test_known_isins_valid(isin):
    assert isin_is_valid(isin)


@pytest.mark.parametrize("isin", ["IE00BK5BQT81", "IE00B4L5Y98", "ie00bk5bqt80", "XX"])
def test_bad_isins_rejected(isin):
    assert not isin_is_valid(isin)


def test_invalid_universe_rejected(tmp_path):
    p = tmp_path / "u.toml"
    p.write_text(
        '[[instrument]]\nid="x"\nname="x"\nasset_class="cfd"\ncurrency="EUR"\ntax_category="RC"\n'
        'isin="IE00BK5BQT81"\nproxy={source="alpaca_stock",symbol="X"}\n'
    )
    with pytest.raises(ConfigError) as e:
        load_universe(p)
    assert "asset_class" in str(e.value) and "ISIN" in str(e.value)
