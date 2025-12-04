# Troubleshooting `chutes-inspecto.so`

This succeeds using the Chutes base image:
```bash
# Exit code 0 (success)
docker pull parachutes/python:3.12
docker run --rm --entrypoint "" parachutes/python:3.12 bash -c 'pip install chutes --upgrade >/dev/null 2>&1 && chutes run does_not_exist:chute --generate-inspecto-hash; echo EXIT:$?'
```

This is the `vanilla elbios/xtts-whisper` image, which ships with python:
```bash
# Exit code 139 (SIGSEGV - segmentation fault)
docker pull elbios/xtts-whisper:latest
docker run --rm --entrypoint "" elbios/xtts-whisper:latest bash -c 'pip install chutes --upgrade >/dev/null 2>&1 && chutes run does_not_exist:chute --generate-inspecto-hash; echo EXIT:$?'
```

This is with a built chute using `Image.from_base("elbios/xtts-whisper:latest")`:
```bash
# Exit code 139 (SIGSEGV - segmentation fault)
chutes build deploy_example_xtts_whisper:chute --wait --local
docker run --rm --entrypoint "" xtts-whisper:tts-stt-v0.1.1 bash -c 'pip install chutes --upgrade >/dev/null 2>&1 && chutes run does_not_exist:chute --generate-inspecto-hash; echo EXIT:$?'
```