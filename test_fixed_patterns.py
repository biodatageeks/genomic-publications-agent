#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspace')

def main():
    print("Testing improved coordinate patterns...")
    
    try:
        from src.analysis.bio_ner.coordinates_recognizer import CoordinatesRecognizer
        recognizer = CoordinatesRecognizer()
        
        # Critical test cases that were failing before
        improved_tests = [
            ("c.*123A>G", "UTR position"),
            ("p.Arg123Ter", "Stop codon"),
            ("p.Val143del", "Protein deletion"),
            ("m.8993T>G", "Mitochondrial"),
            ("o.123A>G", "Circular DNA"),
            ("c.123+10A>G", "Intronic position"),
            ("p.Val600=", "Equal variant"),
            ("r.123delA", "RNA deletion"),
            ("NM_000546.5:c.123A>G", "Dotted identifier"),
            ("t(9;22)(q34;q11.2)", "Complex translocation"),
        ]
        
        print(f"\nTesting {len(improved_tests)} improved patterns:")
        
        passed = 0
        for coord, desc in improved_tests:
            text = f"The variant {coord} was found."
            coords = recognizer.extract_coordinates_regex(text)
            
            if coords and any(coord.lower() in c['coordinate'].lower() for c in coords):
                print(f"✅ {desc}: {coord}")
                passed += 1
            else:
                print(f"❌ {desc}: {coord}")
        
        accuracy = (passed / len(improved_tests)) * 100
        print(f"\nImproved patterns: {passed}/{len(improved_tests)} ({accuracy:.1f}%)")
        
        return accuracy >= 80
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print("\nStatus:", "✅ GOOD" if success else "❌ NEEDS WORK")