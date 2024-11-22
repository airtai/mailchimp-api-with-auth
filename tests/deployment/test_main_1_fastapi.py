from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import UploadFile
from fastapi.testclient import TestClient

from mailchimp_api.deployment.main_1_fastapi import _save_file, app


class TestApp:
    client = TestClient(app)

    @pytest.fixture(autouse=True)
    def patch_uploaded_files_dir(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> Path:
        uploaded_files_dir = tmp_path / "uploads"
        uploaded_files_dir.mkdir(exist_ok=True)

        monkeypatch.setattr(
            "mailchimp_api.deployment.main_1_fastapi.UPLOADED_FILES_DIR",
            uploaded_files_dir,
        )

        # Return the temporary directory so it can be used in tests if needed
        return uploaded_files_dir

    def test_save_file(self) -> None:
        csv_content = "email\nexample1@example.com\nexample2@example.com"
        csv_file = BytesIO(csv_content.encode("utf-8"))
        uploaded_file = UploadFile(filename="emails.csv", file=csv_file)
        path = _save_file(uploaded_file, "22-09-2021")
        df = pd.read_csv(path)

        expected_df = pd.DataFrame(
            {"email": ["example1@example.com", "example2@example.com"]}
        )
        assert df.equals(expected_df)

    def test_upload_file_endpoint(self) -> None:
        timestamp = "22-09-2021"
        response = self.client.get(f"/upload-file?timestamp={timestamp}")
        assert response.status_code == 200
        assert timestamp in response.text

    def test_upload_endpoint(self) -> None:
        csv_content = "email\nemail@gmail.com\n"
        csv_file = BytesIO(csv_content.encode("utf-8"))

        response = self.client.post(
            "/upload",
            files={"file": ("emails.csv", csv_file)},
            data={"timestamp": "test-22-09-2021"},
        )
        assert response.status_code == 200
        expected_msg = "Successfully uploaded emails.csv. Please close the tab and go back to the chat."
        assert expected_msg == response.json()["message"]

    def test_upload_endpoint_raises_400_error_if_file_isnt_provided(self) -> None:
        response = self.client.post("/upload", data={"timestamp": "test-22-09-2021"})
        assert response.status_code == 400
        assert "Please provide .csv file" in response.text

    def test_upload_endpoint_raises_400_error_if_file_is_not_csv(self) -> None:
        csv_content = "email\n"
        csv_file = BytesIO(csv_content.encode("utf-8"))
        response = self.client.post(
            "/upload",
            files={"file": ("emails.txt", csv_file)},
            data={"timestamp": "test-22-09-2021"},
        )
        assert response.status_code == 400
        assert "Only CSV files are supported" in response.text

    def test_upload_endpoint_raises_400_error_if_email_column_not_found(self) -> None:
        csv_content = "name\n"
        csv_file = BytesIO(csv_content.encode("utf-8"))
        response = self.client.post(
            "/upload",
            files={"file": ("emails.csv", csv_file)},
            data={"timestamp": "test-22-09-2021"},
        )
        assert response.status_code == 400
        assert "'email' column not found in CSV file" in response.text
