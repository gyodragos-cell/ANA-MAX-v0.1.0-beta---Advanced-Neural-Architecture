"""Quick analysis script for ana_orchestrator.py using large_file_reader_hyper"""

from tools.large_file_reader_ultimate import LargeFileReaderHyperTool

tool = LargeFileReaderHyperTool()
result = tool.execute(
    file_path='tools/ana_orchestrator.py',
    chunk_size=1500,
    max_chunks=1,
    integrate_memory=False,
    integrate_context=False,
)

print('=== COMPREHENSIVE ANA ORCHESTRATOR ANALYSIS ===')
print()

if result.status == 'success':
    metadata = result.data.get('metadata', {})
    print('FILE METADATA:')
    print('  Path:', metadata.get('path'))
    print('  Size:', metadata.get('size_human'))
    print('  Lines:', metadata.get('total_lines'))
    print('  Extension:', metadata.get('extension'))
    print('  Encoding:', metadata.get('encoding'))
    print()
    
    print('CODE METRICS:')
    print('  Structure hint:', metadata.get('structure_hint'))
    print('  Code/Text:', metadata.get('code_vs_text_hint'))
    print('  Entropy:', f"{metadata.get('entropy_bits_per_byte', 0):.3f} bits/byte")
    print('  Avg line length:', f"{metadata.get('avg_line_length', 0):.1f}")
    print('  Comment ratio:', f"{metadata.get('comment_ratio', 0):.3f}")
    print('  Blank ratio:', f"{metadata.get('blank_ratio', 0):.3f}")
    print()
    
    print('ANOMALY DETECTION:')
    anomalies = metadata.get('anomaly_hints', [])
    if anomalies:
        for anomaly in anomalies:
            print('  -', anomaly)
    else:
        print('  No anomalies detected')
    print()
    
    chunks = result.data.get('chunks', [])
    if chunks:
        content = chunks[0]
        print('STRUCTURE ANALYSIS:')
        class_count = content.count('class ')
        def_count = content.count('def ')
        import_count = content.count('import ')
        from_count = content.count('from ')
        
        print('  Classes:', class_count)
        print('  Functions:', def_count)
        print('  Import statements:', import_count)
        print('  From statements:', from_count)
        print()
        
        # Check for key components
        has_hyper_summary = 'HyperSummary' in content
        has_task_result = 'TaskResult' in content
        has_step = 'class Step' in content
        has_orchestrator = 'class AnaOrchestrator' in content
        has_file_detection = '_detect_file_analysis_need' in content
        has_memory_integration = 'memory_cortex' in content
        has_context_integration = 'context_engine' in content
        has_self_evolving = 'self_evolving' in content
        has_proactive_interrupt = 'proactive_interrupt' in content
        
        print('OS27 HYPER INTEGRATION CHECK:')
        print('  HyperSummary:', '✓' if has_hyper_summary else '✗')
        print('  TaskResult:', '✓' if has_task_result else '✗')
        print('  Step dataclass:', '✓' if has_step else '✗')
        print('  AnaOrchestrator:', '✓' if has_orchestrator else '✗')
        print('  File detection:', '✓' if has_file_detection else '✗')
        print('  Memory integration:', '✓' if has_memory_integration else '✗')
        print('  Context integration:', '✓' if has_context_integration else '✗')
        print('  Self-evolving:', '✓' if has_self_evolving else '✗')
        print('  Proactive interrupt:', '✓' if has_proactive_interrupt else '✗')
        print()
        
        print('LARGE_FILE_READER_HYPER INTEGRATION:')
        has_lfr = 'large_file_reader_hyper' in content
        has_lfr_tool = 'LargeFileReaderHyperTool' in content
        print('  Tool registered:', '✓' if has_lfr else '✗')
        print('  Tool imported:', '✓' if has_lfr_tool else '✗')
        print()
