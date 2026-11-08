"""INSEE idBank mapping: locating the ZIP link on the metadata page."""

import pytest

from fetchers.insee_idbank_resolver import latest_mapping_zip_url


def test_picks_newest_vintage_across_language_and_file_id():
    html = (
        '<a href="/fr/statistiques/fichier/2862759/202605_correspondance_idbank_dimension.zip">'
        '<a href="/en/statistiques/fichier/2868055/202610_correspondance_idbank_dimension.zip">'
        '<a href="/en/statistiques/fichier/2868055/202610_liste_variables_modalites.zip">'
    )
    assert latest_mapping_zip_url(html) == (
        "https://www.insee.fr/en/statistiques/fichier/2868055/202610_correspondance_idbank_dimension.zip"
    )


def test_raises_when_no_link():
    with pytest.raises(RuntimeError, match="No mapping ZIP link"):
        latest_mapping_zip_url("<html>nothing here</html>")
