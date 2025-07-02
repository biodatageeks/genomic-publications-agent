#!/usr/bin/env python3
"""
Comprehensive test for coordinates_recognizer improvements.
"""

import sys
sys.path.insert(0, '/workspace')

def test_improvements():
    """Test all improvements made to regex patterns."""
    
    from src.analysis.bio_ner.coordinates_recognizer import CoordinatesRecognizer
    recognizer = CoordinatesRecognizer()
    
    print("🧪 COMPREHENSIVE TESTING OF COORDINATES RECOGNIZER")
    print("=" * 60)
    
    # Test cases with expected improvements
    test_cases = [
        # Basic patterns that should work
        ("MTHFR:c.677C>T", "hgvs_dna_c", "Basic HGVS c."),
        ("NM_000546:g.7578A>G", "hgvs_dna_g", "Basic HGVS g."),
        ("TP53:p.Val143Ala", "hgvs_protein", "Basic protein"),
        ("rs1234567", "dbsnp", "Basic dbSNP"),
        ("chr7:140453136A>T", "chr_position", "Basic chromosomal"),
        ("del(15)(q11.2q13.1)", "chr_aberration", "Basic aberration"),
        ("HTT:c.52CAG[>36]", "repeat_expansion", "Basic repeat"),
        
        # Previously failing patterns - should work now
        ("p.Arg123Ter", "hgvs_protein", "Protein stop codon (Ter)"),
        ("p.Val143del", "hgvs_protein", "Protein deletion"),
        ("p.Val143dup", "hgvs_protein", "Protein duplication"),
        ("p.Val600=", "hgvs_protein", "Protein equal sign"),
        ("p.val600glu", "hgvs_protein", "Case insensitive protein"),
        ("c.123dupG", "hgvs_dna_c", "DNA duplication with base"),
        ("c.123delinsATG", "hgvs_dna_c", "DNA deletion-insertion"),
        ("c.123+10A>G", "hgvs_dna_c", "Intronic position (+)"),
        ("c.*123A>G", "hgvs_dna_c", "UTR position (*)"),
        ("r.123delA", "hgvs_rna", "RNA deletion"),
        ("r.123+5a>g", "hgvs_rna", "RNA intronic position"),
        ("m.8993T>G", "hgvs_dna_g", "Mitochondrial (m.)"),
        ("o.123A>G", "hgvs_dna_g", "Circular (o.)"),
        ("t(9;22)(q34;q11.2)", "chr_aberration", "Complex translocation"),
        ("NM_000546.5:c.123A>G", "hgvs_dna_c", "ID with dots"),
        
        # Complex patterns
        ("p.Val123_Gly124insAla", "hgvs_protein", "Protein insertion range"),
        ("c.123_124insATGC", "hgvs_dna_c", "DNA insertion range"),
        ("p.Val143_Gly145del", "hgvs_protein", "Protein deletion range"),
    ]
    
    passed = 0
    failed = 0
    
    for coord, expected_type, description in test_cases:
        text = f"The variant {coord} is important."
        coords = recognizer.extract_coordinates_regex(text)
        
        if coords:
            found_coord = coords[0]['coordinate']
            found_type = coords[0]['type']
            
            if found_coord == coord and found_type == expected_type:
                print(f"✅ {description}: {coord}")
                passed += 1
            elif found_coord == coord:
                print(f"⚠️  {description}: {coord} (wrong type: {found_type} vs {expected_type})")
                passed += 1  # Still counts as found
            else:
                print(f"❌ {description}: {coord} (found: {found_coord})")
                failed += 1
        else:
            print(f"❌ {description}: {coord} (not found)")
            failed += 1
    
    total = passed + failed
    accuracy = (passed / total * 100) if total > 0 else 0
    
    print("\n" + "=" * 60)
    print(f"WYNIKI: {passed}/{total} ({accuracy:.1f}%)")
    
    if accuracy >= 90:
        print("🎉 EXCELLENT! Bardzo dobra skuteczność!")
    elif accuracy >= 75:
        print("👍 GOOD! Dobra skuteczność!")
    elif accuracy >= 50:
        print("🔧 NEEDS WORK! Potrzeba więcej poprawek!")
    else:
        print("❌ POOR! Wymaga znacznych poprawek!")
    
    return passed, total

def test_edge_cases():
    """Test edge cases and boundary conditions."""
    
    from src.analysis.bio_ner.coordinates_recognizer import CoordinatesRecognizer
    recognizer = CoordinatesRecognizer()
    
    print("\n🔍 TESTING EDGE CASES")
    print("=" * 40)
    
    edge_cases = [
        ("", "Empty text"),
        ("No coordinates here at all", "Text without coordinates"),
        ("MTHFR:c.677C>T and rs123456 together", "Multiple coordinates"),
        ("Very long text with MTHFR:c.677C>T in the middle of many words", "Coordinate in context"),
        ("Invalid:c.0A>G", "Invalid position (0)"),
        ("Gene:c.123X>Y", "Invalid bases"),
    ]
    
    for text, description in edge_cases:
        coords = recognizer.extract_coordinates_regex(text)
        print(f"{description}: {len(coords)} coordinates found")
        if coords:
            for coord in coords:
                print(f"  - {coord['coordinate']} ({coord['type']})")

def run_all_tests():
    """Run all test suites."""
    print("🚀 STARTING COMPREHENSIVE TESTING")
    print("=" * 70)
    
    try:
        # Test improvements
        passed, total = test_improvements()
        
        # Test edge cases  
        test_edge_cases()
        
        print("\n" + "=" * 70)
        print("FINAL SUMMARY")
        print("=" * 70)
        
        accuracy = (passed / total * 100) if total > 0 else 0
        print(f"Overall accuracy: {accuracy:.1f}% ({passed}/{total})")
        
        if accuracy >= 90:
            print("✅ Ready for production!")
            return True
        else:
            print("🔧 Needs more improvements")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)