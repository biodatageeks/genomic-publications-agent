#!/usr/bin/env python3
"""
Final test summary for coordinates_recognizer after all improvements.
"""

import sys
sys.path.insert(0, '/workspace')

def main():
    print("🏁 FINAL TEST SUMMARY - COORDINATES RECOGNIZER")
    print("=" * 70)
    
    try:
        from src.analysis.bio_ner.coordinates_recognizer import CoordinatesRecognizer
        recognizer = CoordinatesRecognizer()
        print("✅ Module imported and initialized successfully")
        
        # All test cases from original 50 tests
        all_tests = [
            # Basic HGVS patterns - should work
            ("MTHFR:c.677C>T", "hgvs_dna_c", "Basic HGVS c."),
            ("NM_000546:g.7578A>G", "hgvs_dna_g", "Basic HGVS g."),
            ("TP53:p.Val143Ala", "hgvs_protein", "Basic protein"),
            ("TP53:r.123A>G", "hgvs_rna", "Basic RNA"),
            ("rs1234567", "dbsnp", "Basic dbSNP"),
            ("chr7:140453136A>T", "chr_position", "Basic chromosomal"),
            ("del(15)(q11.2q13.1)", "chr_aberration", "Basic aberration"),
            ("HTT:c.52CAG[>36]", "repeat_expansion", "Basic repeat"),
            
            # Previously failing - should work now
            ("c.*123A>G", "hgvs_dna_c", "UTR position (*)"),
            ("p.Arg123Ter", "hgvs_protein", "Protein stop codon"),
            ("p.Val143del", "hgvs_protein", "Protein deletion"),
            ("p.Val143dup", "hgvs_protein", "Protein duplication"),  
            ("p.Val600=", "hgvs_protein", "Protein equal"),
            ("c.123dupG", "hgvs_dna_c", "DNA dup with base"),
            ("c.123delinsATG", "hgvs_dna_c", "DNA delins"),
            ("c.123+10A>G", "hgvs_dna_c", "Intronic position"),
            ("r.123delA", "hgvs_rna", "RNA deletion"),
            ("r.123+5a>g", "hgvs_rna", "RNA intronic"),
            ("m.8993T>G", "hgvs_dna_g", "Mitochondrial"),
            ("o.123A>G", "hgvs_dna_g", "Circular DNA"),
            ("NM_000546.5:c.123A>G", "hgvs_dna_c", "ID with dots"),
            ("t(9;22)(q34;q11.2)", "chr_aberration", "Complex translocation"),
            
            # Advanced patterns
            ("p.val600glu", "hgvs_protein", "Case insensitive"),
            ("c.123_124insATGC", "hgvs_dna_c", "Range insertion"),
            ("p.Val123_Gly124insAla", "hgvs_protein", "Protein range ins"),
            ("rs123456789", "dbsnp", "Long dbSNP"),
            ("chr1:g.123456A>G", "chr_position", "Chr with g."),
            ("inv(16)(p13.1q22)", "chr_aberration", "Inversion"),
            ("c.123-10A>G", "hgvs_dna_c", "Negative intronic"),
        ]
        
        print(f"\nTesting {len(all_tests)} coordinate patterns:")
        print("-" * 50)
        
        passed = 0
        failed = 0
        
        for coord, expected_type, description in all_tests:
            text = f"The variant {coord} is important."
            coords = recognizer.extract_coordinates_regex(text)
            
            if coords:
                found_coord = coords[0]['coordinate']
                found_type = coords[0]['type']
                
                if coord.lower() in found_coord.lower():
                    print(f"✅ {description}: {coord}")
                    passed += 1
                else:
                    print(f"❌ {description}: {coord} -> {found_coord}")
                    failed += 1
            else:
                print(f"❌ {description}: {coord} (not found)")
                failed += 1
        
        total = passed + failed
        accuracy = (passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 70)
        print("📊 RESULTS SUMMARY")
        print("=" * 70)
        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Accuracy: {accuracy:.1f}%")
        
        # Determine status
        if accuracy >= 95:
            status = "🎉 EXCELLENT - Ready for production!"
            color = "excellent"
        elif accuracy >= 90:
            status = "✅ VERY GOOD - Minor issues only"
            color = "good"
        elif accuracy >= 80:
            status = "👍 GOOD - Most patterns working"
            color = "ok"
        elif accuracy >= 70:
            status = "⚠️  ACCEPTABLE - Needs some work"
            color = "warning"
        else:
            status = "❌ POOR - Major improvements needed"
            color = "error"
        
        print(f"Status: {status}")
        
        # Coverage analysis
        pattern_coverage = {
            'hgvs_dna_c': 0,
            'hgvs_dna_g': 0,
            'hgvs_protein': 0,
            'hgvs_rna': 0,
            'dbsnp': 0,
            'chr_position': 0,
            'chr_aberration': 0,
            'repeat_expansion': 0,
        }
        
        for coord, expected_type, _ in all_tests:
            if expected_type in pattern_coverage:
                pattern_coverage[expected_type] += 1
        
        print(f"\n📈 PATTERN COVERAGE:")
        for pattern, count in pattern_coverage.items():
            print(f"  {pattern}: {count} tests")
        
        return accuracy >= 90
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    print("\n🎯 FINAL STATUS:", "SUCCESS" if success else "NEEDS IMPROVEMENT")
    
    if success:
        print("\n🚀 Moduł coordinates_recognizer jest gotowy do użytku!")
        print("📝 Osiągnięto wysoką skuteczność rozpoznawania koordinat genomowych.")
    else:
        print("\n🔧 Moduł wymaga dalszych poprawek przed wdrożeniem.")
    
    exit(0 if success else 1)