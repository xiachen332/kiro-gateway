module.exports = {
  apps: [
    {
      name: "kiro-gateway",
      cwd: "D:\\红线工作区\\epos\\kiro-gateway",
      script: "D:\\红线工作区\\epos\\kiro-gateway\\main.py",
      interpreter: "python",
      env: {
        PYTHONIOENCODING: "utf-8"
      },
      autorestart: true,
      watch: false,
      max_memory_restart: "500M"
    }
  ]
};
