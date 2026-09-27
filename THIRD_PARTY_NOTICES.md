# Third-party notices

The MIT license in this repository applies to the julia-1-api-server wrapper. The following components remain subject to their upstream licenses. This file identifies the main model and Hugging Face components; it is not a replacement for the license notices distributed with all installed Python and operating-system dependencies.

## Supersonic Labs — Julia-1

- Publisher: Supersonic Labs.
- Source and model card: https://huggingface.co/SupersonicLabs/Julia-1
- Pinned source/checkpoint revision: `a85b127321d580d65176c89ced8273f305745d85`.
- License: Apache License 2.0, as declared by the upstream model repository.
- License text: [licenses/Apache-2.0.txt](licenses/Apache-2.0.txt).

This server uses the upstream Python runtime without modifying its source. Runtime code is installed during setup/build; model weights are downloaded separately at startup. The pinned repository contains no separate root `NOTICE` file. Its model card is retained with the installed runtime at `<python-prefix>/share/doc/julia-1/README.md`; any root license/notice files fetched by the installer are preserved there as well.

Julia-1 builds on [JHU CLSP's mmBERT-small](https://huggingface.co/jhu-clsp/mmBERT-small), as documented in the upstream model card. Refer to that model card for model provenance and evaluation details.

## Hugging Face

- `huggingface-hub` 1.3.5: https://github.com/huggingface/huggingface_hub/tree/v1.3.5
- `transformers` 5.0.0: https://github.com/huggingface/transformers/tree/v5.0.0
- Both projects are licensed under Apache License 2.0; see [licenses/Apache-2.0.txt](licenses/Apache-2.0.txt) and their installed distribution license files for component-specific copyright and attribution notices.

Hugging Face provides the repository hosting and open-source tooling. Supersonic Labs is the publisher of Julia-1. Acknowledgment of hosting does not imply that Hugging Face created or endorses this model or server.

## Redistribution

Keep the applicable third-party license and attribution notices with redistributed components. The Docker image retains installed packages' license files and includes this file plus the Apache-2.0 text at `/usr/share/doc/julia-1-api-server`. If modifying or redistributing upstream components separately, follow their respective license terms, including Apache-2.0 Section 4 where applicable.
