package service

import (
	"bytes"
	"mime/multipart"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/athena/media-service/internal/repository"
	"github.com/glebarez/sqlite"
	"github.com/google/uuid"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// mediaFilesDDL mirrors model.Media's columns for sqlite-backed tests.
const mediaFilesDDL = `
CREATE TABLE media_files (
	id                TEXT PRIMARY KEY,
	reference_id      TEXT,
	customer_id       INTEGER,
	category          TEXT NOT NULL,
	media_type        TEXT NOT NULL,
	original_filename TEXT NOT NULL,
	stored_filename   TEXT NOT NULL,
	content_type      TEXT NOT NULL,
	file_size         INTEGER,
	uploaded_by       TEXT,
	service_name      TEXT,
	channel           TEXT,
	tags              TEXT,
	description       TEXT,
	is_public         NUMERIC NOT NULL DEFAULT false,
	thumbnail         TEXT,
	status            TEXT NOT NULL DEFAULT 'ACTIVE',
	created_at        DATETIME
)`

func newRig(t *testing.T) (*MediaService, *gorm.DB, string) {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{Logger: logger.Default.LogMode(logger.Silent)})
	if err != nil {
		t.Fatalf("open sqlite: %v", err)
	}
	// NOTE: AutoMigrate(&model.Media{}) cannot be used here — the model carries
	// `default:gen_random_uuid()` on ID, which is Postgres-specific and makes
	// sqlite's DDL parser fail. The service assigns the UUID in Go before insert
	// (see doUpload), so the column default is never exercised at runtime and an
	// explicit test schema is faithful to how the table is actually used.
	if err := db.Exec(mediaFilesDDL).Error; err != nil {
		t.Fatalf("migrate: %v", err)
	}
	storage := t.TempDir()
	svc := NewMediaService(repository.NewMediaRepository(db), storage)
	return svc, db, storage
}

// makeFileHeader builds a real *multipart.FileHeader by writing and re-parsing
// a multipart form.
func makeFileHeader(t *testing.T, filename string, content []byte) *multipart.FileHeader {
	t.Helper()
	var buf bytes.Buffer
	mw := multipart.NewWriter(&buf)
	fw, err := mw.CreateFormFile("file", filename)
	if err != nil {
		t.Fatalf("CreateFormFile: %v", err)
	}
	_, _ = fw.Write(content)
	_ = mw.Close()

	req := httptest.NewRequest("POST", "/", &buf)
	req.Header.Set("Content-Type", mw.FormDataContentType())
	if err := req.ParseMultipartForm(1 << 20); err != nil {
		t.Fatalf("ParseMultipartForm: %v", err)
	}
	return req.MultipartForm.File["file"][0]
}

func TestUploadStoresFileInsideStorageDir(t *testing.T) {
	svc, _, storage := newRig(t)

	fh := makeFileHeader(t, "id-card.png", []byte("png-bytes"))
	media, err := svc.UploadForCustomer(42, fh, "IMAGE", "KYC", "national id", "tester")
	if err != nil {
		t.Fatalf("upload: %v", err)
	}

	if media.OriginalFilename != "id-card.png" {
		t.Errorf("originalFilename = %q", media.OriginalFilename)
	}
	if !strings.HasSuffix(media.StoredFilename, ".png") {
		t.Errorf("storedFilename %q does not keep extension", media.StoredFilename)
	}
	if media.CustomerID == nil || *media.CustomerID != 42 {
		t.Errorf("customerId = %v, want 42", media.CustomerID)
	}

	stored := filepath.Join(storage, media.StoredFilename)
	data, err := os.ReadFile(stored)
	if err != nil {
		t.Fatalf("stored file unreadable: %v", err)
	}
	if string(data) != "png-bytes" {
		t.Errorf("stored content = %q", data)
	}
}

func TestUploadRejectsEmptyFile(t *testing.T) {
	svc, _, _ := newRig(t)
	fh := makeFileHeader(t, "empty.pdf", nil)
	if _, err := svc.UploadForCustomer(1, fh, "DOC", "KYC", "", "tester"); err == nil {
		t.Fatal("expected error for empty file")
	}
}

// TestUploadTraversalFilenamesStayInsideStorage feeds hostile filenames and
// asserts nothing is ever written outside the storage root (the Java suite's
// path-traversal protection test).
func TestUploadTraversalFilenamesStayInsideStorage(t *testing.T) {
	svc, _, storage := newRig(t)
	parent := filepath.Dir(storage)

	before := listFiles(t, parent, storage)

	hostiles := []string{
		"../../../../etc/passwd",
		"..\\..\\evil.exe",
		"innocent.././../x.txt",
		"a./../../../etc/x",
		"...",
	}
	for _, name := range hostiles {
		fh := makeFileHeader(t, name, []byte("attack"))
		media, err := svc.UploadForCustomer(1, fh, "DOC", "KYC", "", "attacker")
		if err != nil {
			continue // rejection is fine
		}
		// If accepted, the stored file must resolve inside the storage root.
		abs, _ := filepath.Abs(filepath.Join(storage, media.StoredFilename))
		if !strings.HasPrefix(abs, storage+string(os.PathSeparator)) {
			t.Errorf("filename %q stored outside storage root: %s", name, abs)
		}
		if strings.Contains(media.StoredFilename, "..") && strings.ContainsAny(media.StoredFilename, "/\\") {
			t.Errorf("filename %q produced traversal-looking stored name %q", name, media.StoredFilename)
		}
	}

	after := listFiles(t, parent, storage)
	if after != before {
		t.Errorf("files outside storage dir changed during hostile uploads:\nbefore=%q\nafter=%q", before, after)
	}
}

// listFiles snapshots the names in dir excluding the storage tree itself.
func listFiles(t *testing.T, dir, exclude string) string {
	t.Helper()
	var names []string
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("readdir: %v", err)
	}
	for _, e := range entries {
		if filepath.Join(dir, e.Name()) == exclude {
			continue
		}
		names = append(names, e.Name())
	}
	return strings.Join(names, ",")
}

func TestGetExtension(t *testing.T) {
	cases := []struct {
		in, want string
	}{
		{"report.pdf", ".pdf"},
		{"archive.tar.gz", ".gz"},
		{"noext", ""},
		{"", ""},
		{"trailingdot.", "."},
		{".hidden", ".hidden"},
	}
	for _, tc := range cases {
		if got := getExtension(tc.in); got != tc.want {
			t.Errorf("getExtension(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}

func TestMetadataCacheServesAfterDBDelete(t *testing.T) {
	svc, db, _ := newRig(t)
	fh := makeFileHeader(t, "cached.txt", []byte("hello"))
	media, err := svc.UploadForCustomer(9, fh, "DOC", "KYC", "", "tester")
	if err != nil {
		t.Fatalf("upload: %v", err)
	}

	// Prime the cache.
	if _, err := svc.GetMediaMetadata(media.ID); err != nil {
		t.Fatalf("first metadata read: %v", err)
	}

	// Hard-delete the row behind the service's back; cache must still serve it.
	if err := db.Exec("DELETE FROM media_files").Error; err != nil {
		t.Fatalf("raw delete: %v", err)
	}
	got, err := svc.GetMediaMetadata(media.ID)
	if err != nil {
		t.Fatalf("cached metadata read failed after row delete: %v", err)
	}
	if got.OriginalFilename != "cached.txt" {
		t.Errorf("cached filename = %q", got.OriginalFilename)
	}
}

func TestDownloadMedia(t *testing.T) {
	svc, _, storage := newRig(t)
	fh := makeFileHeader(t, "doc.pdf", []byte("%PDF-1.4"))
	media, _ := svc.UploadForCustomer(3, fh, "DOC", "KYC", "", "tester")

	path, meta, err := svc.DownloadMedia(media.ID)
	if err != nil {
		t.Fatalf("download: %v", err)
	}
	if meta.ID != media.ID {
		t.Errorf("metadata id mismatch")
	}
	if filepath.Dir(path) != storage {
		t.Errorf("download path %q not inside storage %q", path, storage)
	}

	t.Run("missing file on disk", func(t *testing.T) {
		_ = os.Remove(path)
		svc.cache.Flush() // drop cached metadata so the repo is re-consulted
		if _, _, err := svc.DownloadMedia(media.ID); err == nil {
			t.Fatal("expected error when stored file is gone")
		}
	})

	t.Run("unknown id", func(t *testing.T) {
		if _, _, err := svc.DownloadMedia(uuid.New()); err == nil {
			t.Fatal("expected error for unknown media id")
		}
	})
}

func TestDeleteMediaRemovesFileAndRecord(t *testing.T) {
	svc, _, storage := newRig(t)
	fh := makeFileHeader(t, "gone.txt", []byte("bye"))
	media, _ := svc.UploadForCustomer(5, fh, "DOC", "KYC", "", "tester")
	stored := filepath.Join(storage, media.StoredFilename)

	if err := svc.DeleteMedia(media.ID); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if _, err := os.Stat(stored); !os.IsNotExist(err) {
		t.Error("stored file still exists after delete")
	}
	if _, err := svc.GetMediaMetadata(media.ID); err == nil {
		t.Error("metadata still resolvable after delete (cache not evicted or row not removed)")
	}
}
