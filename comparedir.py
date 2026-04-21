#!/usr/bin/env python3
"""
Windows Directory Comparison Tool
Compares source and destination directories to identify differences
"""

import os
import sys

# Ensure UTF-8 encoding for console output
sys.stdout.reconfigure(encoding='utf-8')

import filecmp
import shutil
import uuid
import datetime
from pathlib import Path
from collections import defaultdict

# ===== ERROR LOG CONFIGURATION =====
ERROR_DIR = r"error_logs"  # Directory to store files with path length errors
ERROR_LOG_FILE = r"error_logs/error_log.txt"  # Error log file
# ===================================

# ===== CONFIGURATION - EDIT THESE PATHS =====
# NOTE: Windows has a 260-character path limit. For longer paths, use UNC format: \\?\C:\...
# Avoid special characters like & in paths. Use short test paths first to verify the script works.
SOURCE_DIR = r"C:\Users\nxp09546\NXP\SMO Sensors Collaboration Space - expedited delivery\SharePoint Datasets\SP161_Contractors_CHAD\Chad Archive\MEMS Design\GCELL_CrossAxis"  # Set your source directory here
DEST_DIR = r"C:\Users\nxp09546\NXP\M&A Maverick - expedited delivery\SharePoint Datasets\SP161_Contractors_CHAD\Chad Archive\MEMS Design\GCELL_CrossAxis"  # Set your destination directory here
AUTO_CONFIRM = True  # Set to True to skip confirmation prompts and auto-copy files
# ============================================


def init_error_logging():
    """Initialize error logging directory and file"""
    try:
        Path(ERROR_DIR).mkdir(parents=True, exist_ok=True)
        # Create error log file if it doesn't exist
        if not Path(ERROR_LOG_FILE).exists():
            Path(ERROR_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(ERROR_LOG_FILE, 'w') as f:
                f.write("=" * 80 + "\n")
                f.write("ERROR LOG - Path Length and OS Errors\n")
                f.write(f"Log initialized: {datetime.datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")
    except Exception as e:
        print(f"Warning: Could not initialize error logging: {e}")


def log_error(error_id, file_path, error_msg, error_type="GENERAL"):
    """Log an error to the error log file"""
    try:
        timestamp = datetime.datetime.now().isoformat()
        log_entry = f"[{timestamp}] ID: {error_id} | Type: {error_type} | File: {file_path}\n"
        log_entry += f"  Error: {error_msg}\n\n"
        
        with open(ERROR_LOG_FILE, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Warning: Could not write to error log: {e}")


def save_error_file_info(error_id, file_path, original_filename):
    """Save information about a problematic file in error directory and copy the actual file"""
    try:
        # Convert string path to Path object if needed
        if isinstance(file_path, str):
            file_path_str = file_path
        else:
            file_path_str = str(file_path)
        
        # Create unique filename with ID
        error_filename = f"{error_id}-{original_filename}"
        error_file_path = Path(ERROR_DIR) / error_filename
        error_info_filename = f"{error_id}-{original_filename}.info.txt"
        error_info_path = Path(ERROR_DIR) / error_info_filename
        
        # Try to copy the actual file to the error directory using multiple methods
        file_copied = False
        try:
            # For long paths (>260 chars), convert to UNC format which Windows supports
            file_to_copy = file_path_str
            if len(file_to_copy) > 260 and not file_to_copy.startswith('\\\\?\\'):
                file_to_copy = '\\\\?\\' + file_to_copy
            
            # Try method 1: os.path.exists() with raw file operations
            if os.path.exists(file_to_copy):
                try:
                    # Use raw file operations (read bytes, write bytes) - most reliable for long paths
                    with open(file_to_copy, 'rb') as src:
                        file_content = src.read()
                    with open(str(error_file_path), 'wb') as dst:
                        dst.write(file_content)
                    file_copied = True
                    log_error(error_id, file_path_str, f"File successfully copied to error directory: {error_filename}", "FILE_COPIED_TO_ERROR_DIR")
                except Exception as raw_op_err:
                    # If raw operations fail, try shutil.copy2() as fallback
                    try:
                        shutil.copy2(file_to_copy, str(error_file_path))
                        file_copied = True
                        log_error(error_id, file_path_str, f"File successfully copied to error directory (fallback method): {error_filename}", "FILE_COPIED_TO_ERROR_DIR")
                    except Exception as shutil_err:
                        log_error(error_id, file_path_str, f"Failed with raw ops: {raw_op_err}. Failed with shutil: {shutil_err}", "ERROR_COPY_FAILED")
            else:
                log_error(error_id, file_path_str, f"Source file not found (path may be inaccessible)", "FILE_NOT_FOUND")
        except Exception as copy_err:
            log_error(error_id, file_path_str, f"Unexpected error during copy: {copy_err}", "ERROR_COPY_FAILED")
        
        # Create a text file with error information
        with open(error_info_path, 'w') as f:
            f.write(f"Error File Information\n")
            f.write(f"=====================\n\n")
            f.write(f"Error ID: {error_id}\n")
            f.write(f"Original Path: {file_path_str}\n")
            f.write(f"Original Filename: {original_filename}\n")
            f.write(f"Path Length: {len(file_path_str)} characters\n")
            f.write(f"Windows Limit: 260 characters\n")
            f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
            if file_copied:
                f.write(f"\nNote: The actual file has been successfully copied to: {error_filename}\n")
            else:
                f.write(f"\nNote: The actual file could not be copied to the error directory.\n")
                f.write(f"      A copy attempt was made but failed. Check error_log.txt for details.\n")
            f.write(f"Consider moving this file to a location with a shorter path.\n")
        
        return str(error_file_path)
    except Exception as e:
        print(f"Warning: Could not save error file info: {e}")
        return None


def compare_directories(source, dest):
    """
    Compare two directories and report differences.
    
    Returns:
        dict: Contains keys 'only_source', 'only_dest', 'diff_files', 'identical'
    """
    results = {
        'only_source': [],
        'only_dest': [],
        'diff_files': [],
        'identical': [],
        'errors': []
    }
    
    # Convert to Path objects
    source_path = Path(source)
    dest_path = Path(dest)
    
    # Validate directories exist
    if not source_path.is_dir():
        results['errors'].append(f"Source directory not found: {source}")
        return results
    
    if not dest_path.is_dir():
        results['errors'].append(f"Destination directory not found: {dest}")
        return results
    
    # Get all files from both directories
    source_files = set()
    dest_files = set()
    
    try:
        for root, dirs, files in os.walk(source_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), source_path)
                source_files.add(rel_path)
    except (PermissionError, OSError) as e:
        results['errors'].append(f"Error reading source directory: {e}")
    
    try:
        for root, dirs, files in os.walk(dest_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), dest_path)
                dest_files.add(rel_path)
    except (PermissionError, OSError) as e:
        results['errors'].append(f"Error reading destination directory: {e}")
    
    # Find differences
    common_files = source_files & dest_files
    
    # Files only in source
    results['only_source'] = sorted(list(source_files - dest_files))
    
    # Files only in destination
    results['only_dest'] = sorted(list(dest_files - source_files))
    
    # Compare common files
    total_common = len(common_files)
    if total_common:
        print(f"\n⏳ Comparing {total_common} common files...")
    
    for index, rel_path in enumerate(sorted(common_files), start=1):
        source_file = source_path / rel_path
        dest_file = dest_path / rel_path
        
        try:
            # Use robust byte-by-byte comparison for long paths
            src_str = str(source_file)
            dst_str = str(dest_file)
            
            # Check if paths are too long for Windows
            if len(src_str) > 260 or len(dst_str) > 260:
                # Try using UNC paths for long paths
                if not src_str.startswith('\\\\?\\'):
                    src_str = '\\\\?\\' + src_str
                if not dst_str.startswith('\\\\?\\'):
                    dst_str = '\\\\?\\' + dst_str
            
            # Compare files using byte-by-byte reading (more reliable than filecmp for long paths)
            try:
                with open(src_str, 'rb') as src_f, open(dst_str, 'rb') as dst_f:
                    # Read files in chunks to handle large files efficiently
                    chunk_size = 8192
                    while True:
                        src_chunk = src_f.read(chunk_size)
                        dst_chunk = dst_f.read(chunk_size)
                        
                        if src_chunk != dst_chunk:
                            results['diff_files'].append(rel_path)
                            break
                        
                        # If both chunks are empty, files are identical
                        if not src_chunk:
                            results['identical'].append(rel_path)
                            break
            except Exception as cmp_err:
                # If byte comparison fails, fall back to filecmp
                if filecmp.cmp(src_str, dst_str, shallow=False):
                    results['identical'].append(rel_path)
                else:
                    results['diff_files'].append(rel_path)
        except (OSError, IOError) as e:
            results['errors'].append(f"Error comparing {rel_path}: {e} (path length: {len(str(source_file))} chars)")
        except Exception as e:
            results['errors'].append(f"Unexpected error comparing {rel_path}: {e}")
        finally:
            if total_common:
                print_compare_progress(index, total_common, rel_path)
    
    if total_common:
        print()  # New line after progress bar
    
    return results


def print_report(results, source_dir=None, dest_dir=None, save_to_file=False):
    """Print comparison report in a readable format and optionally save to file"""
    report_lines = []
    
    # Header
    header = "\n" + "="*80 + "\nDIRECTORY COMPARISON REPORT\n" + "="*80
    report_lines.append(header)
    print(header)
    
    # Add source and destination info if provided
    if source_dir and dest_dir:
        source_info = f"\nSource Directory: {source_dir}\nDestination Directory: {dest_dir}"
        report_lines.append(source_info)
        print(source_info)
    
    # Add timestamp
    timestamp = f"\nReport Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    report_lines.append(timestamp)
    print(timestamp)
    
    if results['errors']:
        error_section = "\n⚠️  ERRORS:"
        report_lines.append(error_section)
        print(error_section)
        for error in results['errors']:
            error_line = f"  - {error}"
            report_lines.append(error_line)
            print(error_line)
        report_lines.append("")  # Add spacing
    
    # Summary
    summary = "\nSummary:"
    report_lines.append(summary)
    print(summary)
    
    total_source = len(results['only_source']) + len(results['diff_files']) + len(results['identical'])
    total_dest = len(results['only_dest']) + len(results['diff_files']) + len(results['identical'])
    
    summary_lines = [
        f"  Total files in source: {total_source}",
        f"  Total files in destination: {total_dest}",
        f"  Identical files: {len(results['identical'])}",
        f"  Different content: {len(results['diff_files'])}",
        f"  Only in source: {len(results['only_source'])}",
        f"  Only in destination: {len(results['only_dest'])}"
    ]
    
    # Add copy statistics if available
    if 'files_copied' in results:
        summary_lines.append(f"  Files successfully copied: {results['files_copied']}")
    if 'path_errors_saved' in results and results['path_errors_saved'] > 0:
        summary_lines.append(f"  Files copied to error directory (path too long): {results['path_errors_saved']}")
    
    for line in summary_lines:
        report_lines.append(line)
        print(line)
    
    # Only in source
    if results['only_source']:
        source_header = f"\n📁 Only in SOURCE ({len(results['only_source'])} files):"
        report_lines.append(source_header)
        print(source_header)
        for file in results['only_source'][:20]:  # Show first 20
            file_line = f"  - {file}"
            report_lines.append(file_line)
            print(file_line)
        if len(results['only_source']) > 20:
            more_line = f"  ... and {len(results['only_source']) - 20} more"
            report_lines.append(more_line)
            print(more_line)
    
    # Only in destination
    if results['only_dest']:
        dest_header = f"\n📁 Only in DESTINATION ({len(results['only_dest'])} files):"
        report_lines.append(dest_header)
        print(dest_header)
        for file in results['only_dest'][:20]:  # Show first 20
            file_line = f"  - {file}"
            report_lines.append(file_line)
            print(file_line)
        if len(results['only_dest']) > 20:
            more_line = f"  ... and {len(results['only_dest']) - 20} more"
            report_lines.append(more_line)
            print(more_line)
    
    # Different files
    if results['diff_files']:
        diff_header = f"\n⚡ Different Content ({len(results['diff_files'])} files):"
        report_lines.append(diff_header)
        print(diff_header)
        diff_note = "  (Will be copied FROM SOURCE to DESTINATION)"
        report_lines.append(diff_note)
        print(diff_note)
        for file in results['diff_files'][:20]:  # Show first 20
            file_line = f"  - {file}"
            report_lines.append(file_line)
            print(file_line)
        if len(results['diff_files']) > 20:
            more_line = f"  ... and {len(results['diff_files']) - 20} more"
            report_lines.append(more_line)
            print(more_line)
    
    footer = "\n" + "="*80 + "\n"
    report_lines.append(footer)
    print(footer)
    
    # Save to file if requested
    if save_to_file:
        report_filename = f"comparison_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            print(f"Report saved to: {report_filename}")
        except Exception as e:
            print(f"Warning: Could not save report to file: {e}")


def get_confirmation(prompt):
    """Get yes/no confirmation from user (or auto-confirm if AUTO_CONFIRM is True)"""
    if AUTO_CONFIRM:
        print(f"\n{prompt} (yes/no): YES (auto-confirmed)")
        return True
    
    while True:
        response = input(f"\n{prompt} (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def print_progress(index, total, current_file, copied, failed):
    """Print a single-line progress bar"""
    bar_length = 30
    percent = index * 100 / total
    filled = int(bar_length * index / total)
    bar = '█' * filled + '-' * (bar_length - filled)
    file_name = current_file if len(current_file) <= 40 else f"...{current_file[-37:]}"
    sys.stdout.write(
        f"\r   [{index}/{total}] {percent:5.1f}% |{bar}| copied={copied} failed={failed} current={file_name}"
    )
    sys.stdout.flush()


def print_compare_progress(index, total, current_file):
    """Print a single-line progress bar for comparison"""
    bar_length = 30
    percent = index * 100 / total if total else 100.0
    filled = int(bar_length * index / total) if total else bar_length
    bar = '█' * filled + '-' * (bar_length - filled)
    file_name = current_file if len(current_file) <= 40 else f"...{current_file[-37:]}"
    sys.stdout.write(
        f"\r   [{index}/{total}] {percent:5.1f}% |{bar}| comparing={file_name}"
    )
    sys.stdout.flush()


def copy_files(source, dest, results):
    """Copy different/missing files from source to destination"""
    source_path = Path(source)
    dest_path = Path(dest)
    
    files_to_copy = results['only_source'] + results['diff_files']
    
    if not files_to_copy:
        print("\n✓ All files are identical. Nothing to copy.\n")
        return 0
    
    print(f"\n📋 Files that need to be copied: {len(files_to_copy)}")
    if files_to_copy[:10]:
        print("   First 10 files:")
        for file in files_to_copy[:10]:
            print(f"     - {file}")
        if len(files_to_copy) > 10:
            print(f"   ... and {len(files_to_copy) - 10} more")
    
    if not get_confirmation("Do you want to copy these files to destination?"):
        print("\n❌ Copy cancelled by user.\n")
        return 0
    
    copied = 0
    failed = 0
    path_errors = 0
    total = len(files_to_copy)
    errors = []
    
    print("\n⏳ Copying files...")
    
    for index, rel_path in enumerate(files_to_copy, start=1):
        src_file = source_path / rel_path
        dst_file = dest_path / rel_path
        src_str = str(src_file)
        dst_str = str(dst_file)
        
        try:
            # Check for path length issues before attempting copy
            if len(src_str) > 260 or len(dst_str) > 260:
                # Generate unique error ID
                error_id = str(uuid.uuid4())[:8]
                original_filename = Path(rel_path).name
                
                # Log the error
                path_len_msg = f"Path too long: source={len(src_str)}, dest={len(dst_str)} (limit: 260)"
                log_error(error_id, src_str, path_len_msg, "PATH_LENGTH")
                
                # Save error file info (pass the Path object, not the string)
                error_file = save_error_file_info(error_id, src_file, original_filename)
                
                path_errors += 1
                failed += 1
                errors.append(f"{rel_path} - PATH LENGTH ERROR (ID: {error_id}) [See {error_file}]")
                print_progress(index, total, rel_path, copied, failed)
                continue
            
            # Create destination directory if it doesn't exist
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            
            # For long paths or special characters, use string paths with UNC format
            src_copy_path = str(src_file)
            dst_copy_path = str(dst_file)
            
            # Add UNC prefix for long paths
            if len(src_copy_path) > 260 and not src_copy_path.startswith('\\\\?\\'):
                src_copy_path = '\\\\?\\' + src_copy_path
            if len(dst_copy_path) > 260 and not dst_copy_path.startswith('\\\\?\\'):
                dst_copy_path = '\\\\?\\' + dst_copy_path
            
            # Copy file using raw bytes (most reliable for long paths)
            try:
                with open(src_copy_path, 'rb') as src:
                    file_content = src.read()
                with open(dst_copy_path, 'wb') as dst:
                    dst.write(file_content)
            except Exception:
                # Fallback to shutil if bytes method fails
                shutil.copy2(src_copy_path, dst_copy_path)
            
            copied += 1
        except (OSError, IOError) as e:
            # Check if it's a path-related error
            error_id = str(uuid.uuid4())[:8]
            original_filename = Path(rel_path).name
            error_msg = f"{type(e).__name__}: {str(e)}"
            
            log_error(error_id, src_str, error_msg, "OS_ERROR")
            save_error_file_info(error_id, src_file, original_filename)
            
            failed += 1
            errors.append(f"{rel_path} - {error_msg} (ID: {error_id})")
        except Exception as e:
            error_id = str(uuid.uuid4())[:8]
            original_filename = Path(rel_path).name
            error_msg = f"{type(e).__name__}: {str(e)}"
            
            log_error(error_id, src_str, error_msg, "UNEXPECTED_ERROR")
            save_error_file_info(error_id, src_file, original_filename)
            
            failed += 1
            errors.append(f"{rel_path} - Unexpected error: {error_msg} (ID: {error_id})")
        finally:
            print_progress(index, total, rel_path, copied, failed)
    
    print()  # New line after progress bar
    
    if errors:
        print("\n⚠️ Some files failed to copy:")
        for error in errors:
            print(f"  - {error}")
    
    if path_errors > 0:
        print(f"\n📋 Path length errors detected: {path_errors}")
        print(f"   Error details saved in: {ERROR_DIR}")
        print(f"   Error log: {ERROR_LOG_FILE}")
    
    print(f"\n✓ Copy complete: {copied} files copied, {failed} failed.\n")
    return copied, path_errors


def main():
    """Main function"""
    # Initialize error logging
    init_error_logging()
    
    print(f"\nComparing directories:")
    print(f"  Source:      {SOURCE_DIR}")
    print(f"  Destination: {DEST_DIR}")
    
    results = compare_directories(SOURCE_DIR, DEST_DIR)
    print_report(results, SOURCE_DIR, DEST_DIR, save_to_file=True)
    
    # Check if there are files that need to be copied
    files_to_copy = results['only_source'] + results['diff_files']
    if files_to_copy:
        if results['errors']:
            print("\n⚠️  Note: Some errors occurred during scanning, but attempting to copy identified files...")
        copied, path_errors_saved = copy_files(SOURCE_DIR, DEST_DIR, results)
        
        # Update results with copy statistics for final report
        results['files_copied'] = copied
        results['path_errors_saved'] = path_errors_saved
        
        # Print final summary report
        print_report(results, SOURCE_DIR, DEST_DIR, save_to_file=True)
    else:
        print("\n✓ All files are identical. Nothing to copy.\n")


if __name__ == "__main__":
    main()
