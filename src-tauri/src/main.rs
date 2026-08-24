#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use tauri::{RunEvent, WindowEvent};

#[allow(dead_code)]
struct SidecarState {
    child: Arc<Mutex<Option<Child>>>,
}

fn get_python_binary() -> (PathBuf, PathBuf) {
    let mut current_dir = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    if current_dir.ends_with("src-tauri") {
        current_dir.pop();
    }

    let venv_python = current_dir.join(".venv").join("bin").join("python3");
    if venv_python.exists() {
        (venv_python, current_dir)
    } else {
        (PathBuf::from("python3"), current_dir)
    }
}

fn spawn_sidecar() -> (Arc<Mutex<Option<Child>>>, PathBuf) {
    let (python_bin, work_dir) = get_python_binary();
    println!("Starting sidecar with {:?} in {:?}", python_bin, work_dir);

    let child = Command::new(&python_bin)
        .current_dir(&work_dir)
        .args(["-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8765"])
        .spawn()
        .map_err(|e| {
            eprintln!("Failed to spawn Python sidecar: {}", e);
            e
        })
        .ok();

    (Arc::new(Mutex::new(child)), work_dir)
}

fn kill_sidecar(child_mutex: &Arc<Mutex<Option<Child>>>) {
    if let Ok(mut lock) = child_mutex.lock() {
        if let Some(mut child) = lock.take() {
            println!("Terminating Python sidecar process...");
            let _ = child.kill();
            let _ = child.wait();
            println!("Python sidecar terminated.");
        }
    }
}

fn main() {
    let (sidecar_process, _) = spawn_sidecar();
    let sidecar_for_events = Arc::clone(&sidecar_process);

    let app = tauri::Builder::default()
        .manage(SidecarState {
            child: Arc::clone(&sidecar_process),
        })
        .on_window_event({
            let sidecar = Arc::clone(&sidecar_for_events);
            move |event| {
                if let WindowEvent::Destroyed = event.event() {
                    kill_sidecar(&sidecar);
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application");

    app.run({
        let sidecar = Arc::clone(&sidecar_for_events);
        move |_app_handle, event| {
            if let RunEvent::ExitRequested { .. } | RunEvent::Exit = event {
                kill_sidecar(&sidecar);
            }
        }
    });
}
