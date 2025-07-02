#!/usr/bin/env python3
"""
Test runner for coordinates_recognizer without external dependencies.
"""

import sys
import os
import traceback

# Add workspace to path
sys.path.insert(0, '/workspace')

def run_basic_tests():
    """Run basic tests without pytest."""
    print("=" * 70)
    print("URUCHAMIANIE TESTÓW COORDINATES_RECOGNIZER")
    print("=" * 70)
    
    try:
        from src.analysis.bio_ner.coordinates_recognizer import CoordinatesRecognizer
        print("✅ Import CoordinatesRecognizer - OK")
    except Exception as e:
        print(f"❌ Import CoordinatesRecognizer - FAILED: {e}")
        return False

    try:
        recognizer = CoordinatesRecognizer()
        print("✅ Inicjalizacja CoordinatesRecognizer - OK")
    except Exception as e:
        print(f"❌ Inicjalizacja CoordinatesRecognizer - FAILED: {e}")
        return False

    # Test basic functionality
    test_cases = [
        ("MTHFR:c.677C>T", "hgvs_dna_c"),
        ("NM_000546:g.7578A>G", "hgvs_dna_g"),
        ("TP53:p.Val143Ala", "hgvs_protein"),
        ("rs1234567", "dbsnp"),
        ("chr7:140453136A>T", "chr_position"),
        ("del(15)(q11.2q13.1)", "chr_aberration"),
        ("HTT:c.52CAG[>36]", "repeat_expansion"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    print("\nTestowanie wzorców regex:")
    
    for coord, expected_type in test_cases:
        try:
            text = f"The variant {coord} is important."
            coords = recognizer.extract_coordinates_regex(text)
            
            if len(coords) == 1 and coords[0]['coordinate'] == coord and coords[0]['type'] == expected_type:
                print(f"✅ {coord} ({expected_type}) - OK")
                passed += 1
            else:
                print(f"❌ {coord} ({expected_type}) - FAILED: {coords}")
        except Exception as e:
            print(f"❌ {coord} ({expected_type}) - ERROR: {e}")
    
    print(f"\nWynik podstawowych testów: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    return passed == total

def test_missing_patterns():
    """Test patterns that were failing in extended tests."""
    print("\n" + "="*50)
    print("TESTOWANIE BRAKÓW Z ROZSZERZONYCH TESTÓW")
    print("="*50)
    
    from src.analysis.bio_ner.coordinates_recognizer import CoordinatesRecognizer
    recognizer = CoordinatesRecognizer()
    
    missing_tests = [
        ("c.*123A>G", "HGVS UTR"),
        ("p.Arg123Ter", "Protein stop codon"),
        ("p.Val143del", "Protein deletion"),
        ("t(9;22)(q34;q11.2)", "Translocation"),
        ("p.val600glu", "Case insensitive protein"),
        ("c.123dupG", "Duplication with bases"),
        ("c.123_124insATGC", "Insertion with multiple bases"),
        ("c.123delinsATG", "Deletion-insertion"),
        ("p.Val123_Gly124insAla", "Protein insertion"),
        ("p.Val600=", "HGVS with equal sign"),
        ("r.123delA", "RNA deletion"),
        ("m.8993T>G", "HGVS m. notation"),
        ("c.123+10A>G", "Positive intronic position"),
        ("p.Val143dup", "Protein duplication"),
        ("o.123A>G", "HGVS o. notation"),
        ("r.123+5a>g", "RNA with intronic positions"),
    ]
    
    found = 0
    for coord, description in missing_tests:
        text = f"The variant {coord} is important."
        coords = recognizer.extract_coordinates_regex(text)
        
        if coords and any(coord.lower() in c['coordinate'].lower() for c in coords):
            print(f"✅ {description}: {coord}")
            found += 1
        else:
            print(f"❌ {description}: {coord} - Not found")
    
    print(f"\nBrakujące wzorce znalezione: {found}/{len(missing_tests)} ({(found/len(missing_tests))*100:.1f}%)")
    return found, len(missing_tests)

def suggest_improvements():
    """Suggest regex improvements based on failing tests."""
    print("\n" + "="*50)
    print("SUGESTIE POPRAWEK REGEX")
    print("="*50)
    
    improvements = [
        ("UTR positions (c.*123A>G)", "Add \\* support to HGVS patterns"),
        ("Protein variants with Ter", "Add 'Ter' to protein patterns"),
        ("Complex translocations", "Improve chr_aberration pattern"),
        ("Case insensitive proteins", "Already supported via re.IGNORECASE"),
        ("Duplications with bases", "Add base sequences after dup"),
        ("Insertions with ranges", "Add range support _start_end"),
        ("Deletion-insertions", "Improve delins patterns"),
        ("Protein ranges", "Add _AminoAcid_AminoAcid patterns"),
        ("HGVS equal sign", "Add = support to all patterns"),
        ("RNA deletions", "Add del[acgu]* to RNA patterns"),
        ("Mitochondrial m.", "Add m\\. pattern"),
        ("Intronic positions", "Add \\+[0-9]+ support"),
        ("Protein duplications", "Add dup support to proteins"),
        ("HGVS o. notation", "Add o\\. pattern"),
        ("RNA intronic", "Add \\+ support to RNA patterns"),
    ]
    
    for issue, suggestion in improvements:
        print(f"• {issue}: {suggestion}")
    
    return improvements

if __name__ == "__main__":
    success = run_basic_tests()
    found, total_missing = test_missing_patterns()
    improvements = suggest_improvements()
    
    print("\n" + "="*70)
    print("PODSUMOWANIE")
    print("="*70)
    print(f"Podstawowe testy: {'✅ PASSED' if success else '❌ FAILED'}")
    print(f"Brakujące wzorce: {found}/{total_missing} znaleziono")
    print(f"Potrzebne poprawki: {len(improvements)}")
    
    if not success:
        print("\n⚠️  Najpierw napraw podstawowe błędy!")
    elif found < total_missing:
        print(f"\n🔧 Potrzeba poprawić {total_missing - found} wzorców regex")
    else:
        print("\n🎉 Wszystkie testy podstawowe przeszły!")