"""
Dungeon & Wallets - Core Module
BIP39 mnemonic generation from various entropy sources.
"""
import hashlib
import secrets
import hmac
import struct
from typing import List, Tuple, Optional
from dataclasses import dataclass

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class DiceRollResult:
    """Result of processing a dice roll"""
    roll_value: int
    accepted: bool
    byte_value: Optional[int] = None


@dataclass
class EntropyStats:
    """Statistics for entropy collection"""
    total_rolls: int
    accepted_rolls: int
    rejected_rolls: int
    bytes_collected: int
    bytes_needed: int = 16

    @property
    def is_complete(self) -> bool:
        return self.bytes_collected >= self.bytes_needed
    
    @property
    def progress_percent(self) -> float:
        return min(100.0, (self.bytes_collected / self.bytes_needed) * 100)


@dataclass
class WalletInfo:
    """Wallet address information"""
    chain: str
    address: str
    path: str
    explorer_url: str


# ============================================================================
# WORDLIST FUNCTIONS
# ============================================================================

def load_wordlist(path: str) -> List[str]:
    """
    Load BIP39 wordlist from file.
    
    Args:
        path: Path to wordlist file (one word per line)
        
    Returns:
        List of 2048 words
        
    Raises:
        FileNotFoundError: If wordlist file not found
        ValueError: If wordlist doesn't have exactly 2048 words
    """
    with open(path, "r", encoding="utf-8") as f:
        words = [w.strip() for w in f.readlines() if w.strip()]
    
    if len(words) != 2048:
        raise ValueError(f"Wordlist must have 2048 words, got {len(words)}")
    
    return words


# ============================================================================
# ENTROPY CONVERSION
# ============================================================================

def bytes_to_bits(b: bytes) -> str:
    """Convert bytes to binary string representation"""
    return "".join(f"{byte:08b}" for byte in b)


def entropy_to_mnemonic(entropy: bytes, wordlist: List[str]) -> str:
    """
    Convert entropy bytes to BIP39 mnemonic phrase.
    
    Args:
        entropy: Raw entropy bytes (16, 20, 24, 28, or 32 bytes)
        wordlist: BIP39 wordlist (2048 words)
        
    Returns:
        Space-separated mnemonic phrase
        
    Raises:
        ValueError: If entropy length is invalid
    """
    if len(entropy) not in (16, 20, 24, 28, 32):
        raise ValueError("Entropy length must be 16/20/24/28/32 bytes (128..256 bits).")
    
    # Calculate checksum
    ent_bits = bytes_to_bits(entropy)
    cs_len = len(entropy) * 8 // 32  # Checksum length in bits
    checksum = bytes_to_bits(hashlib.sha256(entropy).digest())[:cs_len]
    
    # Combine entropy + checksum
    bits = ent_bits + checksum
    
    # Split into 11-bit chunks and convert to word indices
    chunks = [bits[i:i+11] for i in range(0, len(bits), 11)]
    indices = [int(c, 2) for c in chunks]
    
    return " ".join(wordlist[i] for i in indices)


def validate_mnemonic(mnemonic: str, wordlist: List[str]) -> bool:
    """
    Validate a BIP39 mnemonic phrase.
    
    Args:
        mnemonic: Space-separated mnemonic phrase
        wordlist: BIP39 wordlist
        
    Returns:
        True if valid, False otherwise
    """
    words = mnemonic.strip().split()
    
    # Check word count
    if len(words) not in (12, 15, 18, 21, 24):
        return False
    
    # Check all words are in wordlist
    word_set = set(wordlist)
    if not all(w in word_set for w in words):
        return False
    
    # Convert words to indices, then to bits
    indices = [wordlist.index(w) for w in words]
    bits = "".join(f"{i:011b}" for i in indices)
    
    # Split entropy and checksum
    ent_len = len(words) * 11 * 32 // 33
    ent_bits = bits[:ent_len]
    cs_bits = bits[ent_len:]
    
    # Reconstruct entropy bytes
    entropy = bytes(int(ent_bits[i:i+8], 2) for i in range(0, ent_len, 8))
    
    # Verify checksum
    expected_cs = bytes_to_bits(hashlib.sha256(entropy).digest())[:len(cs_bits)]
    
    return cs_bits == expected_cs


# ============================================================================
# ENTROPY SOURCES
# ============================================================================

def random_entropy(length: int = 16) -> bytes:
    """
    Generate cryptographically secure random entropy.
    
    Args:
        length: Number of bytes (16 for 12 words, 32 for 24 words)
        
    Returns:
        Random entropy bytes
    """
    return secrets.token_bytes(length)


def hex_to_entropy(hex_string: str) -> bytes:
    """
    Convert hex string to entropy bytes.
    
    Args:
        hex_string: Hexadecimal string (with optional 0x prefix)
        
    Returns:
        Entropy bytes
        
    Raises:
        ValueError: If hex string is invalid
    """
    hx = hex_string.strip().lower()
    if hx.startswith("0x"):
        hx = hx[2:]
    
    # Validate hex characters
    if not all(c in '0123456789abcdef' for c in hx):
        raise ValueError("Invalid hex characters")
    
    if len(hx) % 2 != 0:
        raise ValueError("Hex string must have even length")
    
    return bytes.fromhex(hx)


def validate_hex_input(hex_string: str, expected_bytes: int = 16) -> Tuple[bool, str]:
    """
    Validate hex input for entropy.
    
    Args:
        hex_string: Input hex string
        expected_bytes: Expected number of bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    hx = hex_string.strip().lower()
    if hx.startswith("0x"):
        hx = hx[2:]
    
    expected_chars = expected_bytes * 2
    
    if len(hx) != expected_chars:
        return False, f"Il faut exactement {expected_chars} caractères hex ({expected_bytes} octets), reçu {len(hx)}"
    
    if not all(c in '0123456789abcdef' for c in hx):
        return False, "Caractères hex invalides (utilise uniquement 0-9 et a-f)"
    
    return True, ""


# ============================================================================
# DICE ROLL ENTROPY
# ============================================================================

def process_dice_roll(d20: int, d100: int) -> DiceRollResult:
    """
    Process a D20 + d100 roll for entropy generation.
    
    Formula: N = (D20-1) * 100 + d100
    Accept if N < 1792; byte = N % 256
    
    Args:
        d20: D20 roll result (1-20)
        d100: d100 roll result (0-99)
        
    Returns:
        DiceRollResult with acceptance status and byte value
        
    Raises:
        ValueError: If roll values are out of range
    """
    if not (1 <= d20 <= 20):
        raise ValueError(f"D20 must be 1-20, got {d20}")
    if not (0 <= d100 <= 99):
        raise ValueError(f"d100 must be 0-99, got {d100}")
    
    roll_value = (d20 - 1) * 100 + d100
    
    if roll_value < 1792:
        return DiceRollResult(
            roll_value=roll_value,
            accepted=True,
            byte_value=roll_value % 256
        )
    else:
        return DiceRollResult(
            roll_value=roll_value,
            accepted=False,
            byte_value=None
        )


def process_n_value(n: int) -> DiceRollResult:
    """
    Process a pre-computed N value (0-1999) for entropy.
    
    Args:
        n: Combined value from dice (0-1999)
        
    Returns:
        DiceRollResult with acceptance status
        
    Raises:
        ValueError: If n is out of range
    """
    if not (0 <= n <= 1999):
        raise ValueError(f"N must be 0-1999, got {n}")
    
    if n < 1792:
        return DiceRollResult(
            roll_value=n,
            accepted=True,
            byte_value=n % 256
        )
    else:
        return DiceRollResult(
            roll_value=n,
            accepted=False,
            byte_value=None
        )


class DiceEntropyCollector:
    """
    Collects entropy from dice rolls with rejection sampling.
    
    Usage:
        collector = DiceEntropyCollector()
        while not collector.is_complete:
            result = collector.add_roll(d20, d100)
            # or: result = collector.add_n_value(n)
        entropy = collector.get_entropy()
    """
    
    def __init__(self, bytes_needed: int = 16):
        self.bytes_needed = bytes_needed
        self._bytes: List[int] = []
        self._total_rolls = 0
        self._rejected_rolls = 0
    
    @property
    def is_complete(self) -> bool:
        return len(self._bytes) >= self.bytes_needed
    
    @property
    def bytes_collected(self) -> int:
        return len(self._bytes)
    
    @property
    def stats(self) -> EntropyStats:
        return EntropyStats(
            total_rolls=self._total_rolls,
            accepted_rolls=len(self._bytes),
            rejected_rolls=self._rejected_rolls,
            bytes_collected=len(self._bytes),
            bytes_needed=self.bytes_needed
        )
    
    def add_roll(self, d20: int, d100: int) -> DiceRollResult:
        """
        Add a D20 + d100 roll.
        
        Args:
            d20: D20 result (1-20)
            d100: d100 result (0-99)
            
        Returns:
            DiceRollResult
        """
        if self.is_complete:
            raise ValueError("Entropy collection already complete")
        
        result = process_dice_roll(d20, d100)
        self._total_rolls += 1
        
        if result.accepted:
            self._bytes.append(result.byte_value)
        else:
            self._rejected_rolls += 1
        
        return result
    
    def add_n_value(self, n: int) -> DiceRollResult:
        """
        Add a pre-computed N value (0-1999).
        
        Args:
            n: Combined dice value
            
        Returns:
            DiceRollResult
        """
        if self.is_complete:
            raise ValueError("Entropy collection already complete")
        
        result = process_n_value(n)
        self._total_rolls += 1
        
        if result.accepted:
            self._bytes.append(result.byte_value)
        else:
            self._rejected_rolls += 1
        
        return result
    
    def get_entropy(self) -> bytes:
        """
        Get collected entropy bytes.
        
        Returns:
            Entropy bytes
            
        Raises:
            ValueError: If not enough bytes collected
        """
        if not self.is_complete:
            raise ValueError(
                f"Need {self.bytes_needed} bytes, only have {len(self._bytes)}"
            )
        return bytes(self._bytes[:self.bytes_needed])
    
    def reset(self):
        """Reset the collector for a new session"""
        self._bytes = []
        self._total_rolls = 0
        self._rejected_rolls = 0


# ============================================================================
# KEY DERIVATION (BIP32/BIP44)
# ============================================================================

def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    """
    Convert mnemonic to BIP39 seed using PBKDF2.
    
    Args:
        mnemonic: Space-separated mnemonic phrase
        passphrase: Optional passphrase
        
    Returns:
        64-byte seed
    """
    mnemonic_bytes = mnemonic.encode('utf-8')
    salt = ('mnemonic' + passphrase).encode('utf-8')
    return hashlib.pbkdf2_hmac('sha512', mnemonic_bytes, salt, 2048)


def _hmac_sha512(key: bytes, data: bytes) -> bytes:
    """HMAC-SHA512"""
    return hmac.new(key, data, hashlib.sha512).digest()


def _derive_key(parent_key: bytes, parent_chain: bytes, index: int) -> Tuple[bytes, bytes]:
    """BIP32 hardened key derivation"""
    if index >= 0x80000000:  # Hardened
        data = b'\x00' + parent_key + struct.pack('>I', index)
    else:
        data = b'\x00' + parent_key + struct.pack('>I', index)
    
    h = _hmac_sha512(parent_chain, data)
    return h[:32], h[32:]


def derive_key_from_path(seed: bytes, path: str) -> bytes:
    """
    Derive private key from seed using BIP32 path.
    
    Args:
        seed: BIP39 seed (64 bytes)
        path: Derivation path (e.g., "m/44'/60'/0'/0/0")
        
    Returns:
        32-byte private key
    """
    # Master key generation
    h = _hmac_sha512(b"Bitcoin seed", seed)
    key = h[:32]
    chain = h[32:]
    
    # Parse and follow path
    for part in path.split('/')[1:]:  # Skip 'm'
        if part.endswith("'"):
            index = int(part[:-1]) + 0x80000000
        else:
            index = int(part)
        key, chain = _derive_key(key, chain, index)
    
    return key


# ============================================================================
# ADDRESS GENERATION
# ============================================================================

def _base58_encode(data: bytes) -> str:
    """Base58 encoding for Bitcoin addresses"""
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    num = int.from_bytes(data, 'big')
    
    if num == 0:
        return alphabet[0]
    
    result = ''
    while num > 0:
        num, remainder = divmod(num, 58)
        result = alphabet[remainder] + result
    
    # Add leading '1's for leading zero bytes
    for byte in data:
        if byte == 0:
            result = alphabet[0] + result
        else:
            break
    
    return result


def private_key_to_eth_address(private_key: bytes) -> str:
    """
    Convert private key to Ethereum address.
    
    Note: This is a simplified implementation. For production,
    use proper secp256k1 library to derive public key.
    
    Args:
        private_key: 32-byte private key
        
    Returns:
        Ethereum address with 0x prefix
    """
    # Simplified: hash the private key 
    # In production, derive public key via secp256k1 and keccak256
    pub_hash = hashlib.sha256(private_key).digest()
    address = '0x' + pub_hash[-20:].hex()
    return address


def private_key_to_btc_address(private_key: bytes) -> str:
    """
    Convert private key to Bitcoin P2PKH address.
    
    Note: This is a simplified implementation. For production,
    use proper secp256k1 library to derive public key.
    
    Args:
        private_key: 32-byte private key
        
    Returns:
        Bitcoin address (P2PKH format)
    """
    # Simplified version
    pubkey_hash = hashlib.new(
        'ripemd160', 
        hashlib.sha256(private_key).digest()
    ).digest()
    
    # Version byte (0x00 for mainnet P2PKH)
    versioned = b'\x00' + pubkey_hash
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    
    return _base58_encode(versioned + checksum)


def derive_wallet_info(mnemonic: str) -> List[WalletInfo]:
    """
    Derive wallet addresses from mnemonic.
    
    Args:
        mnemonic: BIP39 mnemonic phrase
        
    Returns:
        List of WalletInfo for supported chains
    """
    seed = mnemonic_to_seed(mnemonic)
    wallets = []
    
    # Ethereum (BIP44: m/44'/60'/0'/0/0)
    eth_key = derive_key_from_path(seed, "m/44'/60'/0'/0/0")
    eth_address = private_key_to_eth_address(eth_key)
    wallets.append(WalletInfo(
        chain="Ethereum",
        address=eth_address,
        path="m/44'/60'/0'/0/0",
        explorer_url=f"https://etherscan.io/address/{eth_address}"
    ))
    
    # Bitcoin (BIP44: m/44'/0'/0'/0/0)
    btc_key = derive_key_from_path(seed, "m/44'/0'/0'/0/0")
    btc_address = private_key_to_btc_address(btc_key)
    wallets.append(WalletInfo(
        chain="Bitcoin",
        address=btc_address,
        path="m/44'/0'/0'/0/0",
        explorer_url=f"https://www.blockchain.com/explorer/addresses/btc/{btc_address}"
    ))
    
    return wallets


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_word_count_for_entropy(entropy_bytes: int) -> int:
    """Get mnemonic word count for given entropy byte length"""
    return {16: 12, 20: 15, 24: 18, 28: 21, 32: 24}.get(entropy_bytes, 12)


def get_entropy_bytes_for_words(word_count: int) -> int:
    """Get entropy byte length for given word count"""
    return {12: 16, 15: 20, 18: 24, 21: 28, 24: 32}.get(word_count, 16)


def mask_mnemonic(mnemonic: str) -> str:
    """Return masked version of mnemonic for display"""
    words = mnemonic.split()
    return " ".join("████" for _ in words)
