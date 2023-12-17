
class MockDataProvider:
    """Mock data provider for testing, simulating responses from the Blockchain.info API."""

    def __init__(self):

        self.mock_blocks = {
            0: {
                "hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
                "ver": 1,
                "prev_block": "0000000000000000000000000000000000000000000000000000000000000000",
                "mrkl_root": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
                "time": 1231006505,
                "bits": 486604799,
                "next_block": ["00000000839a8e6886ab5951d76f411475428afc90947ee320161bbf18eb6048"],
                "fee": 0,
                "nonce": 2083236893,
                "n_tx": 1,
                "size": 285,
                "block_index": 0,
                "main_chain": True,
                "height": 0,
                "weight": 1140,
                "tx": [
                        {
                            "hash": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
                            "ver": 1,
                            "vin_sz": 1,
                            "vout_sz": 1,
                            "size": 204,
                            "weight": 816,
                            "fee": 0,
                            "relayed_by": "0.0.0.0",
                            "lock_time": 0,
                            "tx_index": 2098408272645986,
                            "double_spend": False,
                            "time": 1231006505,
                            "block_index": 0,
                            "block_height": 0,
                            "inputs": [
                                {
                                    "sequence": 4294967295,
                                    "witness": "",
                                    "script": "04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73",
                                    "index": 0,
                                    "prev_out": {
                                        "n": 4294967295,
                                        "script": "",
                                        "spending_outpoints": [{"n": 0, "tx_index": 2098408272645986}],
                                        "spent": True,
                                        "tx_index": 0,
                                        "type": 0,
                                        "value": 0
                                    }
                                }
                            ],
                            "out": [
                                {
                                    "type": 0,
                                    "spent": False,
                                    "value": 5000000000,
                                    "spending_outpoints": [],
                                    "n": 0,
                                    "tx_index": 2098408272645986,
                                    "script": "4104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac",
                                    "addr": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
                                }
                            ]
                        }
                ]
            },
            1: {
                "hash": "00000000839a8e6886ab5951d76f411475428afc90947ee320161bbf18eb6048",
                "ver": 1,
                "prev_block": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
                "mrkl_root": "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
                "time": 1231469665,
                "bits": 486604799,
                "next_block": ["000000006a625f06636b8bb6ac7b960a8d03705d1ace08b1a19da3fdcc99ddbd"],
                "fee": 0,
                "nonce": 2573394689,
                "n_tx": 1,
                "size": 215,
                "block_index": 1,
                "main_chain": True,
                "height": 1,
                "weight": 860,
                "tx": [
                    {
                        "hash": "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
                        "ver": 1,
                        "vin_sz": 1,
                        "vout_sz": 1,
                        "size": 134,
                        "weight": 536,
                        "fee": 0,
                        "relayed_by": "0.0.0.0",
                        "lock_time": 0,
                        "tx_index": 5352466621385076,
                        "double_spend": False,
                        "time": 1231469665,
                        "block_index": 1,
                        "block_height": 1,
                        "inputs": [
                            {
                                "sequence": 4294967295,
                                "witness": "",
                                "script": "04ffff001d0104",
                                "index": 0,
                                "prev_out": {
                                    "n": 4294967295,
                                    "script": "",
                                    "spending_outpoints": [{"n": 0, "tx_index": 5352466621385076}],
                                    "spent": True,
                                    "tx_index": 0,
                                    "type": 0,
                                    "value": 0
                                }
                            }
                        ],
                        "out": [
                            {
                                "type": 0,
                                "spent": False,
                                "value": 5000000000,
                                "spending_outpoints": [],
                                "n": 0,
                                "tx_index": 5352466621385076,
                                "script": "410496b538e853519c726a2c91e61ec11600ae1390813a627c66fb8be7947be63c52da7589379515d4e0a604f8141781e62294721166bf621e73a82cbf2342c858eeac",
                                "addr": "12c6DSiU4Rq3P4ZxziKxzrL5LmMBrzjrJX"
                            }
                        ]
                    }
                ]
            },
            170: {
                "hash": "00000000d1145790a8694403d4063f323d499e655c83426834d4ce2f8dd4a2ee",
                "ver": 1,
                "prev_block": "000000002a22cfee1f2c846adbd12b3e183d4f97683f85dad08a79780a84bd55",
                "mrkl_root": "7dac2c5666815c17a3b36427de37bb9d2e2c5ccec3f8633eb91a4205cb4c10ff",
                "time": 1231731025,
                "bits": 486604799,
                "next_block": ["00000000c9ec538cab7f38ef9c67a95742f56ab07b0a37c5be6b02808dbfb4e0"],
                "fee": 0,
                "nonce": 1889418792,
                "n_tx": 2,
                "size": 490,
                "block_index": 170,
                "main_chain": True,
                "height": 170,
                "weight": 1960,
                "tx": [
                    {
                        "hash": "b1fea52486ce0c62bb442b530a3f0132b826c74e473d1f2c220bfa78111c5082",
                        "ver": 1,
                        "vin_sz": 1,
                        "vout_sz": 1,
                        "size": 134,
                        "weight": 536,
                        "fee": 0,
                        "relayed_by": "0.0.0.0",
                        "lock_time": 0,
                        "tx_index": 4584978556854081,
                        "double_spend": False,
                        "time": 1231731025,
                        "block_index": 170,
                        "block_height": 170,
                        "inputs": [
                            {
                                "sequence": 4294967295,
                                "witness": "",
                                "script": "04ffff001d0102",
                                "index": 0,
                                "prev_out": {
                                    "n": 4294967295,
                                    "script": "",
                                    "spending_outpoints": [
                                        {
                                            "n": 0,
                                            "tx_index": 4584978556854081
                                        }
                                    ],
                                    "spent": True,
                                    "tx_index": 0,
                                    "type": 0,
                                    "value": 0
                                }
                            }
                        ],
                        "out": [
                            {
                                "type": 0,
                                "spent": False,
                                "value": 5000000000,
                                "spending_outpoints": [],
                                "n": 0,
                                "tx_index": 4584978556854081,
                                "script": "4104d46c4968bde02899d2aa0963367c7a6ce34eec332b32e42e5f3407e052d64ac625da6f0718e7b302140434bd725706957c092db53805b821a85b23a7ac61725bac",
                                "addr": "1PSSGeFHDnKNxiEyFrD1wcEaHr9hrQDDWc"
                            }
                        ]
                    },
                    {
                        "hash": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
                        "ver": 1,
                        "vin_sz": 1,
                        "vout_sz": 2,
                        "size": 275,
                        "weight": 1100,
                        "fee": 0,
                        "relayed_by": "0.0.0.0",
                        "lock_time": 0,
                        "tx_index": 795787923367440,
                        "double_spend": False,
                        "time": 1231731025,
                        "block_index": 170,
                        "block_height": 170,
                        "inputs": [
                            {
                                "sequence": 4294967295,
                                "witness": "",
                                "script": "47304402204e45e16932b8af514961a1d3a1a25fdf3f4f7732e9d624c6c61548ab5fb8cd410220181522ec8eca07de4860a4acdd12909d831cc56cbbac4622082221a8768d1d0901",
                                "index": 0,
                                "prev_out": {
                                    "addr": "12cbQLTFMXRnSzktFkuoG3eHoMeFtpTu3S",
                                    "n": 0,
                                    "script": "410411db93e1dcdb8a016b49840f8c53bc1eb68a382e97b1482ecad7b148a6909a5cb2e0eaddfb84ccf9744464f82e160bfa9b8b64f9d4c03f999b8643f656b412a3ac",
                                    "spending_outpoints": [
                                        {
                                            "n": 0,
                                            "tx_index": 795787923367440
                                        }
                                    ],
                                    "spent": True,
                                    "tx_index": 7092901136679432,
                                    "type": 0,
                                    "value": 5000000000
                                }
                            }
                        ],
                        "out": [
                            {
                                "type": 0,
                                "spent": True,
                                "value": 1000000000,
                                "spending_outpoints": [{"tx_index": 5011701965475923, "n": 0}],
                                "n": 0,
                                "tx_index": 795787923367440,
                                "script": "4104ae1a62fe09c5f51b13905f07f06b99a2f7159b2225f374cd378d71302fa28414e7aab37397f554a7df5f142c21c1b7303b8a0626f1baded5c72a704f7e6cd84cac",
                                "addr": "1Q2TWHE3GMdB6BZKafqwxXtWAWgFt5Jvm3"
                            },
                            {
                                "type": 0,
                                "spent": True,
                                "value": 4000000000,
                                "spending_outpoints": [{"tx_index": 6687795960110968, "n": 0}],
                                "n": 1,
                                "tx_index": 795787923367440,
                                "script": "410411db93e1dcdb8a016b49840f8c53bc1eb68a382e97b1482ecad7b148a6909a5cb2e0eaddfb84ccf9744464f82e160bfa9b8b64f9d4c03f999b8643f656b412a3ac",
                                "addr": "12cbQLTFMXRnSzktFkuoG3eHoMeFtpTu3S"
                            }
                        ]
                    }
                ]
            }
        }
        
        self.mock_txs = {}

    def get_block_json(self, height: int) -> dict:
        """Returns a mock block JSON for the given height."""
        return self.mock_blocks.get(height, {})

    def get_tx_json(self, tx_hash: str) -> dict:
        """Returns a mock transaction JSON for the given transaction hash."""
        return self.mock_txs.get(tx_hash, {})
