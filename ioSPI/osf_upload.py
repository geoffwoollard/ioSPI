"""Module to upload data to OSF.io generated by simSPI TEM Simulator."""
import typing
from pathlib import Path

import requests


class TEMUpload:
    """Class to upload data to OSF.io generated by simSPI TEM Simulator.

    Parameters
    ----------
    token : str
        Personal token from OSF.io with access to dataset (e.g. cryoEM, etc).
    data_node_guid : str, default = "24htr"
        OSF GUID of data node that houses dataset.

    Attributes
    ----------
    headers : dict of type str:str
        Headers containing authorisation token for requests.
    base_url : str
        OSF.io API url base.
    data_node_guid : str
        OSF GUID of data node that houses dataset.

    See Also
    --------
    OSF API documentation : https://developer.osf.io/
    """

    def __init__(self, token: str, data_node_guid: str = "24htr") -> None:

        self.headers = {"Authorization": f"Bearer {token}"}
        self.base_url = "https://api.osf.io/v2/"

        requests.get(self.base_url, headers=self.headers).raise_for_status()

        self.data_node_guid = data_node_guid

    def get_molecule_guid(self, molecule_label: str) -> str:
        """Get GUID of node housing data for given molecule.

        If no existing node with given label is found, a
        new one is created.


        Parameters
        ----------
        molecule_label:str
            Molecule ID from PDB or EMDB used for generating data.

        Returns
        -------
            GUID of molecule node on OSF.io

        See Also
        --------
        Protein Data Bank(PDB) : https://www.rcsb.org/
        EM Data Resouce(EMDB) : https://www.emdataresource.org/
        """
        existing_molecules = self.get_existing_molecules()
        if molecule_label not in existing_molecules:
            return self.post_child_node(self.data_node_guid, molecule_label)
        return existing_molecules[molecule_label]

    def post_child_node(
        self, parent_guid: str, title: str, tags: typing.Optional[str] = None
    ) -> str:
        """Create a new child node in OSF.io.

        Parameters
        ----------
        parent_guid:str
            GUID of parent node.
        title:str
            Title of child node.
        tags: list[sr], optional
            Tags of child node.

        Returns
        -------
        str
            GUID of newly created child node.

        Raises
        ------
        HTTPError
            Raised if POST request to OSF.io fails.
        """
        request_url = f"{self.base_url}nodes/{parent_guid}/children/"

        request_body = {
            "type": "nodes",
            "attributes": {"title": title, "category": "data", "public": True},
        }

        if tags is not None:
            request_body["attributes"]["tags"] = tags

        response = requests.post(
            request_url, headers=self.headers, json={"data": request_body}
        )
        response.raise_for_status()
        return response.json()["data"]["id"]

    def get_existing_molecules(self) -> typing.Dict[str, str]:
        """Get labels and GUIDs molecule nodes in OSF dataset.

        Returns
        -------
        dict of type str : str
            Returns dictionary of node labels mapped to node GUIDs.

        Raises
        ------
        HTTPError
            Raised if GET request to OSF.io fails.
        """
        request_url = f"{self.base_url}nodes/{self.data_node_guid}/children/"
        response = requests.get(request_url, headers=self.headers)
        response.raise_for_status()
        dataset_node_children = response.json()["data"]

        existing_molecules = {
            child["attributes"]["title"]: child["id"] for child in dataset_node_children
        }

        return existing_molecules

    def post_files(self, dataset_guid: str, file_paths: typing.List[str]):
        """Upload files to a node in OSF.io.

        Parameters
        ----------
        dataset_guid : str
            GUID of node where file is to be uploaded.
        file_paths : list[str]
            File paths of files to be uploaded.

        Returns
        -------
        bool
            True if all uploads are successful, false otherwise.
        """
        files_base_url = "http://files.ca-1.osf.io/v1/resources/"
        create_request_url = f"{files_base_url}{dataset_guid}/providers/osfstorage/"
        success = True

        for file_path_string in file_paths:
            file_path = Path(file_path_string)

            query_parameters = f"?kind=file&name={file_path.name}"
            response = requests.put(
                create_request_url + query_parameters, headers=self.headers
            )
            response.raise_for_status()

            file_content = {file_path.name: open(file_path, "rb")}
            data_upload__url = response.json()["data"]["links"]["upload"]

            with open(file_path, "rb") as file_content:
                response = requests.put(
                    data_upload__url, data=file_content, headers=self.headers
                )
                response.raise_for_status()

            if not response.ok:
                print(f"Upload {file_path} failed with code {response.status_code}")
                success = False
            else:
                print(f"Uploaded {file_path} ")

        return success
