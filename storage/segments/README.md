# Recording segments

`VideoSegmentRecorder` accepts camera frames and writes rotating MP4 segments plus JSON metadata sidecars. It can encrypt finalized media with AES-GCM and apply a retention policy. `RecordingCatalog` lists segments and decrypts media only for authenticated local playback requests.
