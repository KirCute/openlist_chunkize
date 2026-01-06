import argparse
import os
import re
import hashlib
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple


def compute_multiple_hashes(file_path: Path, algorithms: List[str]) -> Dict[str, str]:
    hash_objects = {}
    hash_results = {}

    for algo in algorithms:
        hash_objects[algo] = hashlib.new(algo)

    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096 * 1024), b""):
                for hash_obj in hash_objects.values():
                    hash_obj.update(chunk)
    except Exception:
        raise

    for algo, hash_obj in hash_objects.items():
        hash_results[algo] = hash_obj.hexdigest()

    return hash_results


def process_file(file_info: Tuple[Path, argparse.Namespace]) -> str:
    file_path, args = file_info

    try:
        filename = file_path.name
        parent_dir = file_path.parent

        target_dir_name = f"{args.prefix}{filename}"
        target_dir = parent_dir / target_dir_name

        target_dir.mkdir(exist_ok=True)

        target_file = target_dir / "0"
        shutil.move(str(file_path), str(target_file))

        hash_values = compute_multiple_hashes(target_file, args.hashes)

        for algorithm, hash_value in hash_values.items():
            hash_file_name = f"hash_{algorithm}_{hash_value}"
            hash_file = target_dir / hash_file_name
            hash_file.touch()

        return ""

    except Exception as e:
        return f"Fail: {file_path}: {e}"


def collect_files(
    path: str, args: argparse.Namespace
) -> List[Tuple[Path, argparse.Namespace]]:
    files_to_process = []
    skip_count = 0
    skip_pattern = re.compile(args.skip) if args.skip else None

    if os.path.isfile(path):
        file_path = Path(path)
        filename = file_path.name

        if skip_pattern and re.search(skip_pattern, filename):
            skip_count += 1
        else:
            files_to_process.append(file_path)
    else:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(args.prefix)]

            for file in files:
                if skip_pattern and re.search(skip_pattern, file):
                    skip_count += 1
                    continue

                file_path = Path(root) / file
                files_to_process.append(file_path)

    return files_to_process, skip_count


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("path", type=str, help="path to chunkize")

    parser.add_argument("-p", "--prefix", type=str, default="[openlist_chunk]", help="chunk prefix")

    parser.add_argument(
        "-a",
        "--hashes",
        type=str,
        nargs="+",
        choices=["md5", "sha1", "sha256"],
        required=True,
        help="hash types that need to be calculated"
    )

    parser.add_argument("-n", "--num_workers", type=int, default=1, help="number of the hash computing threads")

    parser.add_argument("-s", "--skip", type=str, default="", help="filename regex that need to be skipped")

    parser.add_argument("-v", "--verbose", action="store_true", help="show more logs")

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"error: path '{args.path}' does not exist")
        return

    if args.num_workers < 1:
        args.num_workers = 1

    if args.skip:
        try:
            re.compile(args.skip)
        except re.error as e:
            print(f"error: invalid regex '{args.skip}': {e}")
            return

    files_to_process, skip_count = collect_files(args.path, args)

    if not files_to_process:
        print(f"no files to process (skipped: {skip_count})")
        return

    if args.verbose:
        print(f"processing {len(files_to_process)} files (skipped: {skip_count})")

    processed_count = 0
    failed_count = 0

    if args.verbose:
        with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
            future_to_file = {
                executor.submit(process_file, (file_path, args)): file_path
                for file_path in files_to_process
            }

            for future in as_completed(future_to_file):
                result = future.result()

                if len(result) == 0:
                    processed_count += 1
                else:
                    failed_count += 1
                    print(result)
    else:
        try:
            from tqdm import tqdm

            with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
                futures = [
                    executor.submit(process_file, (file_path, args))
                    for file_path in files_to_process
                ]

                for future in tqdm(
                    as_completed(futures), total=len(futures), desc="Processing files"
                ):
                    result = future.result()

                    if len(result) == 0:
                        processed_count += 1
                    else:
                        failed_count += 1
        except ImportError:
            print("tqdm not installed. Install with: pip install tqdm")
            print("Falling back to simple progress...")

            with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
                future_to_file = {
                    executor.submit(process_file, (file_path, args)): file_path
                    for file_path in files_to_process
                }

                for i, future in enumerate(as_completed(future_to_file), 1):
                    result = future.result()

                    if len(result) == 0:
                        processed_count += 1
                    else:
                        failed_count += 1

                    if i % 10 == 0 or i == len(files_to_process):
                        print(f"Processed {i}/{len(files_to_process)} files")

    print(
        f"\ntotal: {len(files_to_process)}, processed: {processed_count}, "
        f"failed: {failed_count}, skipped: {skip_count}"
    )


if __name__ == "__main__":
    main()
