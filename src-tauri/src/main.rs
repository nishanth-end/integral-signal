#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::sync::{Arc, Mutex};
use tauri::api::process::{Command, CommandChild, CommandEvent};
use tauri::{RunEvent, WindowEvent};

#[allow(dead_code)]
struct SidecarState {
    child: Arc<Mutex<Option<CommandChild>>>,
}

fn spawn_sidecar() -> Arc<Mutex<Option<CommandChild>>> {
    println!("Starting sidecar via Tauri Command::new_sidecar...");

    match Command::new_sidecar("integral-signal-backend") {
        Ok(command) => match command.spawn() {
            Ok((mut rx, child)) => {
                println!("Python sidecar process spawned successfully.");
                tauri::async_runtime::spawn(async move {
                    while let Some(event) = rx.recv().await {
                        match event {
                            CommandEvent::Stdout(line) => println!("[backend stdout] {}", line),
                            CommandEvent::Stderr(line) => eprintln!("[backend stderr] {}", line),
                            CommandEvent::Error(err) => eprintln!("[backend error] {}", err),
                            CommandEvent::Terminated(payload) => {
                                println!("[backend terminated] {:?}", payload);
                                break;
                            }
                            _ => {}
                        }
                    }
                });
                Arc::new(Mutex::new(Some(child)))
            }
            Err(e) => {
                eprintln!("Failed to spawn Python sidecar: {}", e);
                Arc::new(Mutex::new(None))
            }
        },
        Err(e) => {
            eprintln!("Failed to configure Python sidecar: {}", e);
            Arc::new(Mutex::new(None))
        }
    }
}

fn kill_sidecar(child_mutex: &Arc<Mutex<Option<CommandChild>>>) {
    if let Ok(mut lock) = child_mutex.lock() {
        if let Some(child) = lock.take() {
            println!("Terminating Python sidecar process...");
            let _ = child.kill();
            println!("Python sidecar terminated.");
        }
    }
}

fn main() {
    let sidecar_process = spawn_sidecar();
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
