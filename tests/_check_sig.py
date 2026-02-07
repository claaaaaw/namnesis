from namnesis.sigil.eth import sign_message, load_private_key
pk = load_private_key()
sig = sign_message("test", pk)
print(f"Sig type: {type(sig)}")
print(f"Starts with 0x: {sig.startswith('0x')}")
print(f"Length: {len(sig)}")
print(f"First 10 chars: {sig[:10]}")
