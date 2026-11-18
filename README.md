# secure_file_transfer

Prooflane is a research prototype for sharing versioned files. An owner can grant a workspace member permission to preview a file or to preview and download it. If the owner replaces the file, the new version goes through verification again.

## How a file is released

1. The API stores the upload in a private, versioned Amazon S3 bucket and records its version and SHA-256 digest in PostgreSQL.
2. A verification worker reads that exact version, scans it with ClamAV and checks its digest. Amazon SQS carries storage notifications so the application can reconcile verification jobs.
3. When a member opens or downloads a file, the gateway checks the requested action, current file version and expiry of the verification evidence. It retrieves the approved version and verifies its digest before returning the bytes.

## Research

The project compares FIFO, earliest-deadline-first, a fixed priority rule, LightGBM and a temporal graph model for scheduling verification work. A separate offline experiment compares three convolutional networks on file-format recognition using generated office documents.
