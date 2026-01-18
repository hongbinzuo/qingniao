# Windows 链接错误解决方案

## 问题

编译时遇到C++标准库链接错误：
- `undefined reference to 'std::__throw_bad_array_new_length()'`
- `undefined reference to 'std::basic_streambuf<...>::seekpos(...)'`

这是go-duckdb在Windows上使用TDM-GCC的已知兼容性问题。

## 解决方案

### 方案1：尝试链接libstdc++（可能有效）

编辑代码，添加CGO链接标志（但这需要在go-duckdb层面修复，不是我们的代码问题）

### 方案2：使用MSVC编译器（如果可用）

如果系统有Visual Studio，可以尝试使用MSVC编译器。

### 方案3：使用Python实现（推荐，最简单）⭐

由于go-duckdb在Windows上的兼容性问题，**推荐使用Python实现**：

1. **Go程序获取数据，输出JSON**
   - 使用 `abu_kline_fetcher_simple.go`（不需要CGO）
   
2. **Python脚本导入数据库**
   - 创建导入脚本，读取JSON并写入DuckDB

这样可以：
- ✅ 避免CGO问题
- ✅ 利用Go的并发优势获取数据
- ✅ 使用Python的DuckDB库（稳定可靠）

### 方案4：等待go-duckdb修复

这是go-duckdb包的问题，可能需要等待更新。

## 推荐方案：混合实现

1. **Go程序**：获取K线数据，输出JSON
   - 文件：`abu_kline_fetcher_simple.go`（不需要数据库驱动）
   
2. **Python脚本**：读取JSON，导入DuckDB
   - 使用Python的duckdb库（稳定，无CGO问题）

这样可以发挥Go的并发优势，同时避免Windows上的链接问题。



